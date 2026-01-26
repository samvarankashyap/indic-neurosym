#!/usr/bin/env python3
"""
Crawler for Dwipada Bhagavatam from Telugu Wikisource (te.wikisource.org)

Downloads all 206 chapters across 3 kandas and saves them as organized .txt files.

Key differences from Ranganatha Ramayanam crawler:
- All chapters are on single kanda pages (only 3 pages to fetch)
- Content is in <div class="poem"> sections
- Requires SSL verification disabled (cert issue with Wikisource)
"""

import os
import re
import requests
from bs4 import BeautifulSoup, NavigableString
from pathlib import Path
from typing import List, Tuple, Optional
from urllib.parse import quote
import warnings

# Suppress SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Configuration
BASE_URL = "https://te.wikisource.org/wiki/ద్విపదభాగవతము/"

KANDAS = [
    {"name": "MadhuraKanda", "telugu": "మధురాకాండము", "url_slug": "మధురాకాండము", "folder": "01_MadhuraKanda"},
    {"name": "KalyanaKanda", "telugu": "కల్యాణకాండము", "url_slug": "కల్యాణకాండము", "folder": "02_KalyanaKanda"},
    {"name": "JagadabhirakshaKanda", "telugu": "జగదభిరక్షకాండము", "url_slug": "జగదభిరక్షకాండము", "folder": "03_JagadabhirakshaKanda"},
]

OUTPUT_DIR = Path(__file__).parent / "data" / "dwipada_bhagavatam"

# Request settings
TIMEOUT = 60
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


def fetch_page(url: str) -> Optional[str]:
    """Fetch HTML content from a URL with SSL verification disabled."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response.text
    except requests.RequestException as e:
        print(f"  ERROR: Failed to fetch {url}: {e}")
        return None


def extract_footnotes(soup: BeautifulSoup) -> List[Tuple[str, str]]:
    """Extract footnotes from the page.

    Returns:
        List of (marker, text) tuples
    """
    footnotes = []

    # Find footnote references at bottom of page
    for cite in soup.find_all('li', id=re.compile(r'^cite_note-')):
        cite_id = cite.get('id', '')
        match = re.search(r'cite_note-(\d+)', cite_id)
        if match:
            marker = match.group(1)
            text = cite.get_text(strip=True)
            # Remove the "↑" back-reference
            text = re.sub(r'^↑\s*', '', text)
            if text:
                footnotes.append((marker, text))

    return footnotes


def clean_text(text: str) -> str:
    """Clean extracted text by removing extra whitespace."""
    # Remove multiple consecutive newlines (keep max 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    # Remove empty lines at start and end
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return '\n'.join(lines)


def extract_chapter_content(chapter_soup: BeautifulSoup) -> str:
    """Extract clean text content from a chapter's HTML."""
    # Work on a copy to avoid modifying original
    soup = BeautifulSoup(str(chapter_soup), 'lxml')

    # Remove page number markers
    for pagenum in soup.find_all('span', class_='pagenum'):
        pagenum.decompose()

    # Remove footnote superscripts
    for sup in soup.find_all('sup', class_='reference'):
        sup.decompose()

    # Remove ws-noexport elements (navigation, metadata)
    for noexport in soup.find_all(class_='ws-noexport'):
        noexport.decompose()

    # Find poem divs and extract text
    poems = soup.find_all('div', class_='poem')

    if poems:
        lines = []
        for poem in poems:
            # Replace <br> with newlines
            for br in poem.find_all('br'):
                br.replace_with('\n')

            # Get text
            poem_text = poem.get_text()
            lines.append(poem_text)

        text = '\n'.join(lines)
    else:
        # Fallback: get all text
        for br in soup.find_all('br'):
            br.replace_with('\n')
        text = soup.get_text()

    # Clean up
    text = clean_text(text)

    # Remove line numbers like "10", "20" etc. at end of lines
    text = re.sub(r'\s+\d+\s*$', '', text, flags=re.MULTILINE)

    return text


def parse_kanda_page(html: str) -> List[Tuple[str, str]]:
    """Parse a kanda page and extract all chapters.

    Returns:
        List of (title, content) tuples
    """
    soup = BeautifulSoup(html, 'lxml')

    # Find main content area
    content_div = soup.find('div', class_='prp-pages-output')
    if not content_div:
        content_div = soup.find('div', class_='mw-parser-output')

    if not content_div:
        print("  WARNING: Could not find main content div")
        return []

    # Find all chapter headings
    # Pattern: <div class="tiInherit" style="text-align:center;"><p><b>Chapter Title</b>
    chapter_headings = []

    for div in content_div.find_all('div', class_='tiInherit'):
        style = div.get('style', '')
        if 'text-align:center' in style or 'text-align: center' in style:
            # Look for bold text (chapter title)
            bold = div.find('b')
            if bold:
                title = bold.get_text(strip=True)
                # Skip kanda title headers
                if 'కాండము' in title and len(title) < 30:
                    continue
                # Skip very short titles or navigation
                if len(title) < 5:
                    continue
                chapter_headings.append((title, div))

    print(f"  Found {len(chapter_headings)} chapters")

    # Extract content for each chapter
    chapters = []

    for i, (title, heading_div) in enumerate(chapter_headings):
        # Find content between this heading and the next
        content_elements = []
        current = heading_div.next_sibling

        # Get the next heading's div (or end of content)
        next_heading_div = chapter_headings[i + 1][1] if i + 1 < len(chapter_headings) else None

        while current:
            if current == next_heading_div:
                break

            # Check if we've reached another centered heading div
            if hasattr(current, 'get') and current.get('class'):
                if 'tiInherit' in current.get('class', []):
                    style = current.get('style', '')
                    if 'text-align:center' in style or 'text-align: center' in style:
                        bold = current.find('b') if hasattr(current, 'find') else None
                        if bold:
                            break

            content_elements.append(current)
            current = current.next_sibling

        # Create a temporary soup with the content elements
        temp_soup = BeautifulSoup('<div></div>', 'lxml')
        container = temp_soup.find('div')

        for elem in content_elements:
            if isinstance(elem, NavigableString):
                container.append(NavigableString(str(elem)))
            elif hasattr(elem, 'name'):
                container.append(BeautifulSoup(str(elem), 'lxml'))

        # Extract text content
        content = extract_chapter_content(container)

        if content.strip():
            chapters.append((title, content))

    return chapters


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    # Remove or replace invalid filename characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '', name)
    # Replace multiple spaces with single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    # Limit length
    return sanitized[:50].strip() if len(sanitized) > 50 else sanitized.strip()


def format_output(kanda_telugu: str, chapter_num: int, title: str, content: str,
                  footnotes: List[Tuple[str, str]] = None) -> str:
    """Format the chapter content for saving to file."""
    output = []
    output.append(f"# కాండము: {kanda_telugu}")
    output.append(f"# అధ్యాయము: {chapter_num:03d}")
    output.append(f"# శీర్షిక: {title}")
    output.append("")
    output.append(content)

    # Add footnotes if any
    if footnotes:
        output.append("")
        output.append("---")
        output.append("పాదసూచికలు (Footnotes):")
        for marker, text in footnotes:
            output.append(f"[{marker}] {text}")

    return '\n'.join(output)


def crawl_kanda(kanda: dict, output_dir: Path) -> int:
    """Crawl all chapters of a kanda.

    Returns:
        Number of chapters successfully saved
    """
    output_folder = output_dir / kanda['folder']
    output_folder.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Crawling {kanda['name']} ({kanda['telugu']})")
    print(f"{'='*60}")

    # Build URL
    url = BASE_URL + kanda['url_slug']
    print(f"  URL: {url}")

    # Fetch the page
    html = fetch_page(url)
    if not html:
        print(f"  ERROR: Failed to fetch kanda page")
        return 0

    # Parse chapters
    chapters = parse_kanda_page(html)

    if not chapters:
        print(f"  WARNING: No chapters found")
        return 0

    # Save each chapter
    success_count = 0

    for i, (title, content) in enumerate(chapters, 1):
        # Format output
        output_text = format_output(kanda['telugu'], i, title, content)

        # Create filename
        safe_title = sanitize_filename(title)
        filename = f"{i:03d}_{safe_title}.txt" if safe_title else f"{i:03d}.txt"
        filepath = output_folder / filename

        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(output_text)

        success_count += 1
        print(f"  Chapter {i:03d}: {title[:40]}...")

    return success_count


def main():
    """Main function to crawl all kandas."""
    print("="*60)
    print("Dwipada Bhagavatam Crawler")
    print("="*60)
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Total kandas: {len(KANDAS)}")
    print("="*60)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Track statistics
    total_success = 0

    for kanda in KANDAS:
        success = crawl_kanda(kanda, OUTPUT_DIR)
        total_success += success
        print(f"\n{kanda['name']}: {success} chapters saved")

    # Final summary
    print("\n" + "="*60)
    print("CRAWL COMPLETE")
    print("="*60)
    print(f"Total chapters saved: {total_success}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
