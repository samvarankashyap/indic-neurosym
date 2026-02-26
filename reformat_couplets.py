#!/usr/bin/env python3
"""
Reformat ranganatha_ramayanam text files:
1. Remove all blank lines from the verse body (between header and footnotes)
2. Insert a blank line after every 2 lines (couplet)
Footnotes section (after '---') is left unchanged.
"""

import os
import glob


def reformat_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Strip trailing newlines for easier processing
    lines = [line.rstrip('\n') for line in lines]

    # Separate header, body, and footnotes
    header_lines = []
    body_lines = []
    footnote_lines = []

    # Parse header: lines starting with '#' and the blank line after
    i = 0
    while i < len(lines) and lines[i].startswith('#'):
        header_lines.append(lines[i])
        i += 1
    # Skip blank line(s) after header
    while i < len(lines) and lines[i].strip() == '':
        i += 1

    # Find footnotes separator '---'
    footnote_start = None
    for j in range(i, len(lines)):
        if lines[j].strip() == '---':
            footnote_start = j
            break

    # Extract body and footnotes
    if footnote_start is not None:
        body_lines = lines[i:footnote_start]
        footnote_lines = lines[footnote_start:]
    else:
        body_lines = lines[i:]
        footnote_lines = []

    # Remove all blank lines from body
    body_lines = [line for line in body_lines if line.strip() != '']

    # Group into couplets (every 2 lines) and insert blank line between them
    reformatted_body = []
    for idx, line in enumerate(body_lines):
        reformatted_body.append(line)
        # After every 2nd line (completing a couplet), add a blank line
        # but not after the very last line
        if (idx + 1) % 2 == 0 and idx < len(body_lines) - 1:
            reformatted_body.append('')

    # Reassemble the file
    result = []
    result.extend(header_lines)
    result.append('')  # blank line after header
    result.extend(reformatted_body)

    if footnote_lines:
        result.append('')  # blank line before footnotes
        result.extend(footnote_lines)

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result) + '\n')


def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data', 'ranganatha_ramayanam')
    txt_files = sorted(glob.glob(os.path.join(base_dir, '**', '*.txt'), recursive=True))

    print(f"Found {len(txt_files)} files to process")
    for filepath in txt_files:
        rel = os.path.relpath(filepath, base_dir)
        try:
            reformat_file(filepath)
            print(f"  Processed: {rel}")
        except Exception as e:
            print(f"  ERROR processing {rel}: {e}")

    print("Done!")


if __name__ == '__main__':
    main()