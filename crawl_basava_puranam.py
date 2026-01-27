#!/usr/bin/env python3
"""
Crawler for బసవపురాణము (Basava Puranam) from Telugu Wikisource (te.wikisource.org)

Downloads all sections from 3 ఆశ్వాసములు and saves them as organized .txt files
in a nested directory structure.

Key features:
- 3 ఆశ్వాసములు, each on a separate page
- Each ఆశ్వాసము has multiple sections (విషయానుక్రమణిక)
- Content is extracted from poem divs and paragraph tags
- Requires SSL verification disabled (cert issue with Wikisource)
"""

import os
import re
import requests
from bs4 import BeautifulSoup, NavigableString
from pathlib import Path
from typing import List, Tuple, Optional
import warnings
import time

# Suppress SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Configuration
ASHVASAMS = [
    {
        "num": 1,
        "name": "ప్రథమాశ్వాసము",
        "url": "https://te.wikisource.org/wiki/బసవపురాణము/ప్రథమాశ్వాసము",
        "folder": "001_ప్రథమాశ్వాసము"
    },
    {
        "num": 2,
        "name": "ద్వితీయాశ్వాసము",
        "url": "https://te.wikisource.org/wiki/బసవపురాణము/ద్వితీయాశ్వాసము",
        "folder": "002_ద్వితీయాశ్వాసము"
    },
    {
        "num": 3,
        "name": "తృతీయాశ్వాసము",
        "url": "https://te.wikisource.org/wiki/బసవపురాణము/తృతీయాశ్వాసము",
        "folder": "003_తృతీయాశ్వాసము"
    },
]

OUTPUT_DIR = Path(__file__).parent / "data" / "basava_puranam"

# Request settings
TIMEOUT = 60
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


def fetch_page(url: str, retries: int = 3) -> Optional[str]:
    """Fetch HTML content from a URL with SSL verification disabled."""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.RequestException as e:
            print(f"  Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    print(f"  ERROR: Failed to fetch {url} after {retries} attempts")
    return None


def clean_text(text: str) -> str:
    """Clean extracted text by removing extra whitespace and citations."""
    # Remove citation markers [1], [2], etc.
    text = re.sub(r'\[\d+\]', '', text)

    # Remove standalone numbers at line ends (page numbers)
    text = re.sub(r'\s+\d+\s*$', '', text, flags=re.MULTILINE)

    # Remove hyphens from page breaks
    text = re.sub(r'-\s*\n\s*', '', text)

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


def extract_section_content(section_soup: BeautifulSoup) -> str:
    """Extract clean text content from a section's HTML."""
    # Work on a copy to avoid modifying original
    soup = BeautifulSoup(str(section_soup), 'lxml')

    # Remove page number markers
    for pagenum in soup.find_all('span', class_='pagenum'):
        pagenum.decompose()

    # Remove footnote superscripts
    for sup in soup.find_all('sup', class_='reference'):
        sup.decompose()

    # Remove ws-noexport elements (navigation, metadata)
    for noexport in soup.find_all(class_='ws-noexport'):
        noexport.decompose()

    # Remove edit section links
    for edit_link in soup.find_all('span', class_='mw-editsection'):
        edit_link.decompose()

    # Collect text from multiple sources
    all_text_parts = []

    # Find poem divs and extract text
    poems = soup.find_all('div', class_='poem')
    for poem in poems:
        for br in poem.find_all('br'):
            br.replace_with('\n')
        poem_text = poem.get_text()
        if poem_text.strip():
            all_text_parts.append(poem_text)

    # Also look for direct <p> tags (not inside poems)
    for p in soup.find_all('p'):
        # Skip if this <p> is inside a poem div (already extracted)
        if p.find_parent('div', class_='poem'):
            continue
        for br in p.find_all('br'):
            br.replace_with('\n')
        p_text = p.get_text()
        if p_text.strip():
            all_text_parts.append(p_text)

    if all_text_parts:
        text = '\n'.join(all_text_parts)
    else:
        # Ultimate fallback: get all text
        for br in soup.find_all('br'):
            br.replace_with('\n')
        text = soup.get_text()

    # Clean up
    text = clean_text(text)

    return text


def parse_ashvasam(html: str, ashvasam_name: str) -> List[Tuple[str, str]]:
    """Parse an ఆశ్వాసము page and extract all sections.

    Returns:
        List of (title, content) tuples
    """
    soup = BeautifulSoup(html, 'lxml')

    # Find main content area
    content_div = soup.find('div', class_='mw-parser-output')
    if not content_div:
        content_div = soup.find('div', class_='prp-pages-output')

    if not content_div:
        print(f"  WARNING: Could not find main content div for {ashvasam_name}")
        return []

    # Get the HTML string of the content div for position-based extraction
    content_html = str(content_div)

    # Find section headings - Wikisource typically uses h2 or h3 for sections
    # Also check for centered divs with titles
    section_info = []  # List of (title, start_pos, end_pos_of_heading)

    # Method 1: Look for h2/h3 section headers
    for header in content_div.find_all(['h2', 'h3']):
        # Get the headline span inside
        headline = header.find('span', class_='mw-headline')
        if headline:
            title = headline.get_text(strip=True)
        else:
            title = header.get_text(strip=True)

        # Skip very short titles or navigation elements
        if len(title) < 2:
            continue
        # Skip table of contents header
        if title in ['విషయసూచిక', 'విషయానుక్రమణిక', 'Contents']:
            continue

        # Find position
        header_html = str(header)
        pos = content_html.find(header_html)
        if pos != -1:
            section_info.append((title, pos, pos + len(header_html)))

    # Method 2: If no h2/h3 found, look for centered div titles (like Sri Rama Parinayamu)
    if not section_info:
        for div in content_div.find_all('div', class_='tiInherit'):
            style = div.get('style', '')
            if 'text-align:center' in style or 'text-align: center' in style:
                p_tag = div.find('p')
                if p_tag:
                    title = p_tag.get_text(strip=True)
                    if len(title) < 3:
                        continue
                    # Skip book/chapter headers
                    if title == 'బసవపురాణము' or title == ashvasam_name:
                        continue

                    div_html = str(div)
                    pos = content_html.find(div_html)
                    if pos != -1:
                        section_info.append((title, pos, pos + len(div_html)))

    # Method 3: Look for bold centered paragraphs as section headers
    if not section_info:
        for p in content_div.find_all('p'):
            # Check if it looks like a heading (short, possibly bold)
            b_tag = p.find('b')
            if b_tag:
                title = b_tag.get_text(strip=True)
                if len(title) >= 3 and len(title) <= 100:
                    p_html = str(p)
                    pos = content_html.find(p_html)
                    if pos != -1:
                        section_info.append((title, pos, pos + len(p_html)))

    print(f"  Found {len(section_info)} sections in {ashvasam_name}")

    if not section_info:
        # If no sections found, treat the whole page as one section
        content = extract_section_content(content_div)
        if content.strip():
            return [(ashvasam_name, content)]
        return []

    # Extract content for each section based on positions
    sections = []

    for i, (title, start_pos, heading_end_pos) in enumerate(section_info):
        # Content starts after the heading
        content_start = heading_end_pos

        # Content ends at the start of the next heading (or end of content)
        if i + 1 < len(section_info):
            content_end = section_info[i + 1][1]
        else:
            content_end = len(content_html)

        # Extract the HTML chunk for this section
        section_html = content_html[content_start:content_end]

        # Parse and extract text
        content = extract_section_content(BeautifulSoup(section_html, 'lxml'))

        if content.strip():
            sections.append((title, content))

    return sections


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    # Remove or replace invalid filename characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '', name)
    # Replace multiple spaces with single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    # Limit length
    return sanitized[:50].strip() if len(sanitized) > 50 else sanitized.strip()


def format_output(ashvasam_name: str, section_num: int, title: str, content: str) -> str:
    """Format the section content for saving to file."""
    output = []
    output.append("# గ్రంథము: బసవపురాణము")
    output.append(f"# ఆశ్వాసము: {ashvasam_name}")
    output.append(f"# విభాగము: {section_num:03d}")
    output.append(f"# శీర్షిక: {title}")
    output.append("")
    output.append(content)

    return '\n'.join(output)


def crawl_ashvasam(ashvasam: dict) -> int:
    """Crawl a single ఆశ్వాసము and save all its sections.

    Returns:
        Number of sections successfully saved
    """
    print(f"\n{'='*60}")
    print(f"Crawling {ashvasam['name']}")
    print(f"URL: {ashvasam['url']}")
    print(f"{'='*60}")

    # Create output folder
    output_folder = OUTPUT_DIR / ashvasam['folder']
    output_folder.mkdir(parents=True, exist_ok=True)

    # Fetch the page
    print("  Fetching page...")
    html = fetch_page(ashvasam['url'])
    if not html:
        print(f"  ERROR: Failed to fetch page for {ashvasam['name']}")
        return 0

    print(f"  Page fetched successfully ({len(html)} bytes)")

    # Parse sections
    print("  Parsing sections...")
    sections = parse_ashvasam(html, ashvasam['name'])

    if not sections:
        print(f"  WARNING: No sections found for {ashvasam['name']}")
        return 0

    # Save each section
    print(f"  Saving {len(sections)} sections...")
    success_count = 0

    for i, (title, content) in enumerate(sections, 1):
        # Format output
        output_text = format_output(ashvasam['name'], i, title, content)

        # Create filename
        safe_title = sanitize_filename(title)
        filename = f"{i:03d}_{safe_title}.txt" if safe_title else f"{i:03d}.txt"
        filepath = output_folder / filename

        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(output_text)

        success_count += 1
        print(f"    Section {i:03d}: {title[:40]}...")

    return success_count


def main():
    """Main function to crawl all ఆశ్వాసములు."""
    print("=" * 60)
    print("బసవపురాణము (Basava Puranam) Crawler")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Total ఆశ్వాసములు: {len(ASHVASAMS)}")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Track statistics
    total_sections = 0

    for ashvasam in ASHVASAMS:
        sections_saved = crawl_ashvasam(ashvasam)
        total_sections += sections_saved
        print(f"  {ashvasam['name']}: {sections_saved} sections saved")

        # Small delay between pages to be polite
        time.sleep(1)

    # Final summary
    print("\n" + "=" * 60)
    print("CRAWL COMPLETE")
    print("=" * 60)
    print(f"Total sections saved: {total_sections}")
    print(f"Output directory: {OUTPUT_DIR}")

    # List output folders
    print("\nOutput folders:")
    for ashvasam in ASHVASAMS:
        folder = OUTPUT_DIR / ashvasam['folder']
        if folder.exists():
            file_count = len(list(folder.glob("*.txt")))
            print(f"  {ashvasam['folder']}: {file_count} files")


if __name__ == "__main__":
    main()
