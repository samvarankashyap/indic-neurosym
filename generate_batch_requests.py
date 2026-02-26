#!/usr/bin/env python3
"""
Generate Vertex AI batch request JSONL from dwipada couplets.

Reads all .txt files under data/, extracts dwipada couplets, and writes
a JSONL file where each line is a Vertex AI batch prediction request
asking for bhavam and prathipadartham of the couplet.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
OUTPUT_FILE = OUTPUT_DIR / "batch_requests.jsonl"

PROMPT_TEMPLATE = (
    "Assume role of a telugu and sanskrit scholar and give me bhavam and "
    "prathipadartham of the following dwipada poem. If there are combined "
    "words please break them with + in prathipadartham. Further bhavam "
    "should be in single line in telugu and English. Just give only bhavam "
    "and prathipadartham of the given input. No additional data."
)

# Pattern to match editorial annotations like [వా.రా. సర్గ 5]
ANNOTATION_PATTERN = re.compile(r"\[.*?\]")

# Pattern to detect damaged/missing text lines
DOT_PATTERN = re.compile(r"…|\.{4,}")


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def extract_couplets(filepath: Path) -> Tuple[List[Tuple[str, str]], int, int]:
    """
    Extract dwipada couplets from a single text file.

    Filtering pipeline:
        1. Stop at '---' (footnotes section)
        2. Remove lines starting with '#' (metadata/comments)
        3. Remove blank lines
        4. Strip [annotation] brackets from remaining lines
        5. Pair lines sequentially into couplets
        6. Discard couplets where either line has dots/ellipsis
        7. Discard orphan last line if odd count

    Args:
        filepath: Path to the .txt file

    Returns:
        Tuple of (couplets_list, orphan_count, dot_discarded_count)
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    # Step 1-3: Filter lines (stop at footnotes, skip # and blanks)
    clean_lines = []
    for line in raw_lines:
        stripped = line.strip()

        # Stop at footnotes section
        if stripped == "---":
            break

        # Skip comments and blank lines
        if stripped.startswith("#") or not stripped:
            continue

        # Step 4: Strip editorial annotations
        cleaned = ANNOTATION_PATTERN.sub("", stripped).strip()
        if cleaned:
            clean_lines.append(cleaned)

    # Step 5: Pair sequentially
    orphan_count = len(clean_lines) % 2
    pairs = []
    for i in range(0, len(clean_lines) - orphan_count, 2):
        pairs.append((clean_lines[i], clean_lines[i + 1]))

    # Step 6: Discard couplets with dots/ellipsis in either line
    dot_discarded = 0
    valid_couplets = []
    for line1, line2 in pairs:
        if DOT_PATTERN.search(line1) or DOT_PATTERN.search(line2):
            dot_discarded += 1
        else:
            valid_couplets.append((line1, line2))

    return valid_couplets, orphan_count, dot_discarded


def build_request(line1: str, line2: str, source_file: str, work: str, couplet_num: int) -> dict:
    """
    Build a single Vertex AI batch request dict.

    Args:
        line1: First line of the couplet
        line2: Second line of the couplet
        source_file: Relative path to the source .txt file
        work: Name of the literary work (top-level folder under data/)
        couplet_num: Couplet number within the file (1-based)

    Returns:
        Dict in Vertex AI batch prediction format with metadata
    """
    prompt_text = f"{PROMPT_TEMPLATE}\nPoem:\n{line1}\n{line2}"

    return {
        "request": {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt_text}]
                }
            ]
        },
        "metadata": {
            "source_file": source_file,
            "work": work,
            "couplet_number": couplet_num
        }
    }


def find_txt_files(data_dir: Path) -> List[Path]:
    """Find all .txt files under data_dir, sorted for deterministic order."""
    txt_files = sorted(data_dir.rglob("*.txt"))
    return txt_files


def get_work_name(filepath: Path, data_dir: Path) -> str:
    """Extract the work name (first directory under data/) from a file path."""
    relative = filepath.relative_to(data_dir)
    return relative.parts[0] if relative.parts else "unknown"


def main():
    if not DATA_DIR.exists():
        print(f"Error: Data directory '{DATA_DIR}' not found.", file=sys.stderr)
        sys.exit(1)

    # Find all text files
    txt_files = find_txt_files(DATA_DIR)
    print(f"Found {len(txt_files)} .txt files in {DATA_DIR}/")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Process all files
    total_couplets = 0
    total_orphans = 0
    total_dot_discarded = 0
    files_with_orphans = 0
    files_with_dots = 0

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for filepath in txt_files:
            couplets, orphans, dot_discarded = extract_couplets(filepath)
            work = get_work_name(filepath, DATA_DIR)
            source = str(filepath)

            for idx, (line1, line2) in enumerate(couplets, start=1):
                request = build_request(line1, line2, source, work, idx)
                out_f.write(json.dumps(request, ensure_ascii=False) + "\n")

            total_couplets += len(couplets)
            total_orphans += orphans
            total_dot_discarded += dot_discarded
            if orphans:
                files_with_orphans += 1
            if dot_discarded:
                files_with_dots += 1

    # Summary
    print(f"\n{'=' * 60}")
    print(f"BATCH REQUEST GENERATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Files processed:        {len(txt_files)}")
    print(f"  Couplets written:       {total_couplets}")
    print(f"  Couplets discarded (…): {total_dot_discarded} (from {files_with_dots} files)")
    print(f"  Orphan lines skipped:   {total_orphans} (from {files_with_orphans} files)")
    print(f"  Output file:            {OUTPUT_FILE}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
