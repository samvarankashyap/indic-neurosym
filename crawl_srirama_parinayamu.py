#!/usr/bin/env python3
"""
Crawler for శ్రీరమాపరిణయము (Sri Rama Parinayamu) from Telugu Wikisource (te.wikisource.org)

Downloads all 28 chapters by తరిగొండ వెంగమాంబ and saves them as organized .txt files.

Key features:
- All 28 chapters are on a single page (only 1 request needed)
- Content is in <div class="poem"> sections
- Requires SSL verification disabled (cert issue with Wikisource)
"""

import os
import re
import requests
from bs4 import BeautifulSoup, NavigableString
from pathlib import Path
from typing import List, Tuple, Optional
import warnings

# Suppress SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Configuration
PAGE_URL = "https://te.wikisource.org/wiki/శ్రీరమాపరిణయము/పాఠం"
OUTPUT_DIR = Path(__file__).parent / "data" / "srirama_parinayamu"

# Request settings
TIMEOUT = 60
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Expected chapters (for validation)
EXPECTED_CHAPTERS = [
    "ఇష్టదేవతా స్తుతి",
    "నారాయణుని దేవతలు ప్రార్థించుట",
    "నారాయణుని యనుగ్రహోక్తి",
    "శ్రీహరి వేంకటాద్రికి విచ్చేయుట",
    "శ్రీహరి బ్రహ్మాదులను క్షీరాబ్ధికడకు గన్య నడుగ బంపుట",
    "సముద్రుని సంప్రశ్నము",
    "బ్రహ్మాదులు కన్య నడుగుట",
    "బ్రహ్మాదులు స్వామికి వివాహ నిశ్చయ మెఱిగించుట",
    "పెండ్లి పయనము",
    "వరపూజ",
    "పేరంటము పిలుపు",
    "పెండ్లి యేర్పాట్లు",
    "స్వామి కల్యాణము",
    "బువ్వము బంతి",
    "శంకర, శ్రీహరుల వావిపల్కులు",
    "భుక్తశేష వినోదము - వితరణ",
    "పార్వతీదేవి మాటకారితనము",
    "పరమేశ్వరుని పరియాచకములు",
    "స్వామి సరసోక్తులు",
    "సాగరుని సమన్వయము",
    "కనక కలశ చౌర్యము - కన్యక అభ్యర్థనము",
    "శ్రీహరి యాహ్వానము - శేషాద్రికి బ్రయాణము",
    "సాగరుని సంప్రార్థనము",
    "వకుళమాలిక పలుకులు",
    "సముద్రుని హితవచనములు",
    "సాగరుని మనవి",
    "శ్రీనివాసుని వైభవము",
    "కృతి సమర్పణము",
]


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
                import time
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


def extract_chapter_content(chapter_soup: BeautifulSoup) -> str:
    """Extract clean text content from a chapter's HTML.

    This page has content in both <div class="poem"> and directly in <p> tags,
    so we collect from all sources to ensure nothing is missed.
    """
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

    # Collect text from multiple sources:
    # 1. <div class="poem"> sections
    # 2. Direct <p> tags
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
    # that contain Telugu verse content
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


def parse_page(html: str) -> List[Tuple[str, str]]:
    """Parse the main page and extract all chapters.

    Uses string-position based extraction since chapter headings may not be siblings.

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

    # Get the HTML string of the content div for position-based extraction
    content_html = str(content_div)

    # Find all chapter headings with their positions
    # Pattern: <div class="tiInherit" style="text-align:center;"><p>Chapter Title</p>
    chapter_info = []  # List of (title, start_pos, end_pos_of_heading)

    for div in content_div.find_all('div', class_='tiInherit'):
        style = div.get('style', '')
        if 'text-align:center' in style or 'text-align: center' in style:
            p_tag = div.find('p')
            if p_tag:
                title = p_tag.get_text(strip=True)
                # Skip very short titles or navigation
                if len(title) < 3:
                    continue
                # Skip book title header
                if title == 'శ్రీరమాపరిణయము':
                    continue
                # Skip if it's a subtitle
                if 'ద్విపద కావ్యము' in title:
                    continue

                # Find position of this div in the HTML string
                div_html = str(div)
                pos = content_html.find(div_html)
                if pos != -1:
                    chapter_info.append((title, pos, pos + len(div_html)))

    print(f"  Found {len(chapter_info)} chapters")

    # Extract content for each chapter based on positions
    chapters = []

    for i, (title, start_pos, heading_end_pos) in enumerate(chapter_info):
        # Content starts after the heading
        content_start = heading_end_pos

        # Content ends at the start of the next heading (or end of content)
        if i + 1 < len(chapter_info):
            content_end = chapter_info[i + 1][1]
        else:
            content_end = len(content_html)

        # Extract the HTML chunk for this chapter
        chapter_html = content_html[content_start:content_end]

        # Parse and extract text
        content = extract_chapter_content(BeautifulSoup(chapter_html, 'lxml'))

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


def format_output(chapter_num: int, title: str, content: str) -> str:
    """Format the chapter content for saving to file."""
    output = []
    output.append("# గ్రంథము: శ్రీరమాపరిణయము")
    output.append("# రచయిత: తరిగొండ వెంగమాంబ")
    output.append(f"# అధ్యాయము: {chapter_num:03d}")
    output.append(f"# శీర్షిక: {title}")
    output.append("")
    output.append(content)

    return '\n'.join(output)


def main():
    """Main function to crawl all chapters."""
    print("=" * 60)
    print("శ్రీరమాపరిణయము (Sri Rama Parinayamu) Crawler")
    print("=" * 60)
    print(f"Source: {PAGE_URL}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Expected chapters: {len(EXPECTED_CHAPTERS)}")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch the page
    print("\nFetching page...")
    html = fetch_page(PAGE_URL)
    if not html:
        print("ERROR: Failed to fetch the page")
        return

    print(f"  Page fetched successfully ({len(html)} bytes)")

    # Parse chapters
    print("\nParsing chapters...")
    chapters = parse_page(html)

    if not chapters:
        print("WARNING: No chapters found")
        return

    # Save each chapter
    print(f"\nSaving {len(chapters)} chapters...")
    success_count = 0

    for i, (title, content) in enumerate(chapters, 1):
        # Format output
        output_text = format_output(i, title, content)

        # Create filename
        safe_title = sanitize_filename(title)
        filename = f"{i:03d}_{safe_title}.txt" if safe_title else f"{i:03d}.txt"
        filepath = OUTPUT_DIR / filename

        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(output_text)

        success_count += 1
        print(f"  Chapter {i:03d}: {title[:40]}...")

    # Final summary
    print("\n" + "=" * 60)
    print("CRAWL COMPLETE")
    print("=" * 60)
    print(f"Total chapters saved: {success_count}")
    print(f"Output directory: {OUTPUT_DIR}")

    # Validation
    if success_count != len(EXPECTED_CHAPTERS):
        print(f"\nWARNING: Expected {len(EXPECTED_CHAPTERS)} chapters, got {success_count}")


if __name__ == "__main__":
    main()
