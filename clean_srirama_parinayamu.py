#!/usr/bin/env python3
"""
Clean the Sri Rama Parinayamu dataset by removing punctuation marks.

Removes:
- All kinds of quotes (single, double, Telugu quotes)
- Exclamation marks
- Hyphens
- Telugu arasunna (ఁ - chandrabindu)
- Question marks
- Commas
- Other punctuation
"""

import re
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "srirama_parinayamu"

# Characters to remove (using Unicode escapes for clarity)
CHARS_TO_REMOVE = [
    # Single quotes (ASCII and Unicode curly)
    "'",            # U+0027 ASCII apostrophe
    "\u2018",       # U+2018 left single quotation mark '
    "\u2019",       # U+2019 right single quotation mark '
    # Double quotes (ASCII and Unicode curly)
    '"',            # U+0022 ASCII double quote
    "\u201C",       # U+201C left double quotation mark "
    "\u201D",       # U+201D right double quotation mark "
    "\u201E",       # U+201E double low-9 quotation mark „
    '`', '´',       # Backticks
    '«', '»',       # Guillemets
    # Punctuation
    ',',            # Comma
    '?',            # Question mark
    '!',            # Exclamation
    '-',            # Hyphen
    '–', '—',       # En-dash, Em-dash
    # Telugu specific
    'ఁ',            # Arasunna (chandrabindu)
    # Whitespace
    "\u00A0",       # U+00A0 non-breaking space
    # Other
    ';',            # Semicolon
    ':',            # Colon (but keep in metadata lines)
    '.',            # Period
    '(',  ')',      # Parentheses
    '[', ']',       # Brackets
]


def clean_line(line: str, is_metadata: bool = False) -> str:
    """Clean a single line by removing specified characters.

    Args:
        line: The line to clean
        is_metadata: If True, preserve colons for metadata format
    """
    if is_metadata:
        # For metadata lines (starting with #), only remove specific chars but keep colon
        chars = [c for c in CHARS_TO_REMOVE if c != ':']
    else:
        chars = CHARS_TO_REMOVE

    for char in chars:
        line = line.replace(char, '')

    # Clean up multiple spaces that may result from removals
    line = re.sub(r'  +', ' ', line)

    return line


def clean_file(filepath: Path) -> tuple[int, int]:
    """Clean a single file.

    Returns:
        Tuple of (lines_processed, chars_removed)
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_len = len(content)

    lines = content.split('\n')
    cleaned_lines = []

    for line in lines:
        # Check if it's a metadata line
        is_metadata = line.startswith('#')
        cleaned_lines.append(clean_line(line, is_metadata))

    cleaned_content = '\n'.join(cleaned_lines)
    chars_removed = original_len - len(cleaned_content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)

    return len(lines), chars_removed


def main():
    """Clean all files in the dataset."""
    print("=" * 60)
    print("Cleaning Sri Rama Parinayamu Dataset")
    print("=" * 60)
    print(f"Directory: {DATA_DIR}")
    print(f"Characters to remove: {CHARS_TO_REMOVE}")
    print("=" * 60)

    files = sorted(DATA_DIR.glob("*.txt"))
    print(f"Found {len(files)} files to clean\n")

    total_lines = 0
    total_chars_removed = 0

    for filepath in files:
        lines, chars_removed = clean_file(filepath)
        total_lines += lines
        total_chars_removed += chars_removed
        print(f"  {filepath.name[:50]}... - {chars_removed} chars removed")

    print("\n" + "=" * 60)
    print("CLEANING COMPLETE")
    print("=" * 60)
    print(f"Files processed: {len(files)}")
    print(f"Total lines: {total_lines}")
    print(f"Total characters removed: {total_chars_removed}")


if __name__ == "__main__":
    main()
