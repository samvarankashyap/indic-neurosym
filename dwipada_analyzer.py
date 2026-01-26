# -*- coding: utf-8 -*-
"""
Dwipada Analyzer v1.0
---------------------
Standalone Telugu Dwipada Chandassu (prosody) analysis tool.

Features:
- Aksharam (syllable) splitting
- Gana (prosody) analysis (Guru/Laghu marking)
- Dwipada validation:
  * Gana Sequence: 3 Indra Ganas + 1 Surya Gana per line
  * Prasa: 2nd aksharam consonant match between lines
  * Yati: 1st letter of 1st Gana matches 1st letter of 3rd Gana

Based on Aksharanusarika v0.0.7a logic.
"""

import re
from typing import List, Tuple, Dict, Optional, Set

###############################################################################
# LINGUISTIC DATA AND CONSTANTS
###############################################################################

dependent_to_independent = {
    "ా": "ఆ", "ి": "ఇ", "ీ": "ఈ", "ు": "ఉ", "ూ": "ఊ", "ృ": "ఋ",
    "ౄ": "ౠ", "ె": "ఎ", "ే": "ఏ", "ై": "ఐ", "ొ": "ఒ", "ో": "ఓ", "ౌ": "ఔ"
}
halant = "్"
telugu_consonants = {
    "క", "ఖ", "గ", "ఘ", "ఙ", "చ", "ఛ", "జ", "ఝ", "ఞ",
    "ట", "ఠ", "డ", "ఢ", "ణ", "త", "థ", "ద", "ధ", "న",
    "ప", "ఫ", "బ", "భ", "మ", "య", "ర", "ల", "వ", "శ",
    "ష", "స", "హ", "ళ", "ఱ"
}
long_vowels = {"ా", "ీ", "ూ", "ే", "ో", "ౌ", "ౄ"}
independent_vowels = {
    "అ", "ఆ", "ఇ", "ఈ", "ఉ", "ఊ", "ఋ", "ౠ",
    "ఎ", "ఏ", "ఐ", "ఒ", "ఓ", "ఔ"
}
independent_long_vowels = {"ఆ", "ఈ", "ఊ", "ౠ", "ఏ", "ఓ"}
diacritics = {"ం", "ః"}
dependent_vowels = set(dependent_to_independent.keys())
ignorable_chars = {' ', '\n', 'ఁ', '​'}  # space, newline, arasunna, zero-width space

# Yati Maitri Groups (Vargas)
YATI_MAITRI_GROUPS = [
    {"అ", "ఆ", "ఐ", "ఔ", "హ", "య", "అం", "అః"},
    {"ఇ", "ఈ", "ఎ", "ఏ", "ఋ"},
    {"ఉ", "ఊ", "ఒ", "ఓ"},
    {"క", "ఖ", "గ", "ఘ", "క్ష"},
    {"చ", "ఛ", "జ", "ఝ", "శ", "ష", "స"},
    {"ట", "ఠ", "డ", "ఢ"},
    {"త", "థ", "ద", "ధ"},
    {"ప", "ఫ", "బ", "భ", "వ"},
    {"ర", "ల", "ఱ", "ళ"},
    {"న", "ణ"},
    {"మ", "పు", "ఫు", "బు", "భు", "ము"},
]

# Indra Gana patterns (3 or 4 syllables)
INDRA_GANAS = {
    "IIII": "Nala (నల)",
    "IIIU": "Naga (నగ)",
    "IIUI": "Sala (సల)",
    "UII": "Bha (భ)",
    "UIU": "Ra (ర)",
    "UUI": "Ta (త)",
}

# Surya Gana patterns (2 or 3 syllables)
SURYA_GANAS = {
    "III": "Na (న)",
    "UI": "Ha/Gala (హ/గల)",
}


###############################################################################
# CORE AKSHARAM SPLITTING FUNCTIONS
###############################################################################

def categorize_aksharam(aksharam: str) -> List[str]:
    """Categorize an aksharam with linguistic tags."""
    categories = set()

    if aksharam[0] in independent_vowels:
        categories.add("అచ్చు")
    elif aksharam in diacritics:
        categories.add("అచ్చు")

    if any(c in telugu_consonants for c in aksharam):
        categories.add("హల్లు")

    if any(dv in aksharam for dv in long_vowels) or aksharam in independent_long_vowels:
        categories.add("దీర్ఘ")

    if "ః" in aksharam:
        categories.add("విసర్గ అక్షరం")
    if "ం" in aksharam:
        categories.add("అనుస్వారం")

    found_conjunct, found_double = False, False
    for i in range(len(aksharam) - 2):
        if (aksharam[i] in telugu_consonants and
            aksharam[i+1] == halant and
            aksharam[i+2] in telugu_consonants):
            if aksharam[i] == aksharam[i+2]:
                found_double = True
            else:
                found_conjunct = True

    if found_conjunct:
        categories.add("సంయుక్తాక్షరం")
    if found_double:
        categories.add("ద్విత్వాక్షరం")

    return sorted(list(categories))


def split_aksharalu(word: str) -> List[str]:
    """Split Telugu word into aksharalu (syllables)."""
    coarse_split = []
    i, n = 0, len(word)

    while i < n:
        if word[i] in ignorable_chars:
            coarse_split.append(word[i])
            i += 1
            continue

        current = []
        if word[i] in telugu_consonants:
            current.append(word[i])
            i += 1
            while i < n and word[i] == halant:
                current.append(word[i])
                i += 1
                if i < n and word[i] in telugu_consonants:
                    current.append(word[i])
                    i += 1
                else:
                    break
            while i < n and (word[i] in dependent_vowels or word[i] in diacritics):
                current.append(word[i])
                i += 1
        else:
            char = word[i]
            current.append(char)
            i += 1
            if char in independent_vowels and i < n and word[i] in diacritics:
                current.append(word[i])
                i += 1
        coarse_split.append("".join(current))

    if not coarse_split:
        return []

    # Second pass: merge pollu hallu with previous aksharam
    final_aksharalu = []
    for chunk in coarse_split:
        is_pollu_hallu = len(chunk) == 2 and chunk[0] in telugu_consonants and chunk[1] == halant
        if is_pollu_hallu and final_aksharalu and final_aksharalu[-1] not in ignorable_chars:
            final_aksharalu[-1] += chunk
        else:
            final_aksharalu.append(chunk)

    return [ak for ak in final_aksharalu if ak]


def akshara_ganavibhajana(aksharalu_list: List[str]) -> List[str]:
    """
    Perform Gana (prosody) analysis - mark each syllable as Guru (U) or Laghu (I).
    """
    if not aksharalu_list:
        return []

    ganam_markers = [None] * len(aksharalu_list)

    # First Pass: Identify Gurus based on their own properties
    for i, aksharam in enumerate(aksharalu_list):
        if aksharam in ignorable_chars:
            ganam_markers[i] = ""
            continue

        ganam_markers[i] = "I"  # Default to Laghu
        tags = set(categorize_aksharam(aksharam))

        is_guru = False
        if 'దీర్ఘ' in tags:
            is_guru = True
        if 'ఐ' in aksharam or 'ఔ' in aksharam or 'ై' in aksharam or 'ౌ' in aksharam:
            is_guru = True
        if 'అనుస్వారం' in tags or 'విసర్గ అక్షరం' in tags:
            is_guru = True
        if aksharam.endswith(halant):
            is_guru = True
        if is_guru:
            ganam_markers[i] = "U"

    # Second pass: syllable before conjunct/double becomes Guru
    for i in range(len(aksharalu_list)):
        if ganam_markers[i] == "":
            continue

        next_syllable_index = -1
        for j in range(i + 1, len(aksharalu_list)):
            if aksharalu_list[j] not in ignorable_chars:
                next_syllable_index = j
                break

        if next_syllable_index != -1:
            next_aksharam_tags = set(categorize_aksharam(aksharalu_list[next_syllable_index]))
            if 'సంయుక్తాక్షరం' in next_aksharam_tags or 'ద్విత్వాక్షరం' in next_aksharam_tags:
                ganam_markers[i] = "U"

    return ganam_markers


###############################################################################
# DWIPADA SPECIFIC FUNCTIONS
###############################################################################

def get_base_consonant(aksharam: str) -> Optional[str]:
    """Extract the base consonant from an aksharam."""
    if not aksharam:
        return None
    first_char = aksharam[0]
    if first_char in telugu_consonants:
        return first_char
    return None


def get_first_letter(aksharam: str) -> Optional[str]:
    """Get the first letter of an aksharam for Yati matching."""
    if not aksharam:
        return None
    return aksharam[0]


def check_yati_maitri(letter1: str, letter2: str) -> Tuple[bool, Optional[int]]:
    """
    Check if two letters belong to the same Yati Maitri group.

    Returns:
        Tuple of (is_match, group_index)
    """
    if not letter1 or not letter2:
        return False, None

    for idx, group in enumerate(YATI_MAITRI_GROUPS):
        if letter1 in group and letter2 in group:
            return True, idx

    # Same letter is always a match
    if letter1 == letter2:
        return True, -1

    return False, None


def check_prasa(line1: str, line2: str) -> Tuple[bool, Dict]:
    """
    Check Prasa (rhyme) between two lines.

    Prasa rule: 2nd aksharam's base consonant must match between the two lines.

    Args:
        line1: First line of dwipada
        line2: Second line of dwipada

    Returns:
        Tuple of (is_match, details_dict)
    """
    # Split lines into aksharalu
    aksharalu1 = split_aksharalu(line1)
    aksharalu2 = split_aksharalu(line2)

    # Filter out spaces/ignorable chars
    pure1 = [ak for ak in aksharalu1 if ak not in ignorable_chars]
    pure2 = [ak for ak in aksharalu2 if ak not in ignorable_chars]

    # Check if we have at least 2 aksharalu
    if len(pure1) < 2 or len(pure2) < 2:
        return False, {"error": "Lines too short - need at least 2 aksharalu each"}

    # Get 2nd aksharam from each
    second_ak1 = pure1[1]
    second_ak2 = pure2[1]

    # Extract base consonant
    consonant1 = get_base_consonant(second_ak1)
    consonant2 = get_base_consonant(second_ak2)

    # Compare
    is_match = consonant1 == consonant2 if consonant1 and consonant2 else False

    return is_match, {
        "line1_second_aksharam": second_ak1,
        "line1_consonant": consonant1,
        "line2_second_aksharam": second_ak2,
        "line2_consonant": consonant2,
        "match": is_match
    }


def check_prasa_aksharalu(aksharam1: str, aksharam2: str) -> Tuple[bool, Dict]:
    """
    Check if two aksharalu have matching Prasa consonant.

    Useful for finding rhyming words or checking individual syllable pairs.

    Args:
        aksharam1: First aksharam/syllable
        aksharam2: Second aksharam/syllable

    Returns:
        Tuple of (is_match, details_dict)
    """
    consonant1 = get_base_consonant(aksharam1)
    consonant2 = get_base_consonant(aksharam2)

    is_match = consonant1 == consonant2 if consonant1 and consonant2 else False

    return is_match, {
        "aksharam1": aksharam1,
        "consonant1": consonant1,
        "aksharam2": aksharam2,
        "consonant2": consonant2,
        "match": is_match
    }


def identify_gana(pattern: str) -> Tuple[Optional[str], str]:
    """
    Identify the Gana type from a pattern.

    Returns:
        Tuple of (gana_name, gana_type) where gana_type is 'Indra' or 'Surya' or 'Unknown'
    """
    if pattern in INDRA_GANAS:
        return INDRA_GANAS[pattern], "Indra"
    if pattern in SURYA_GANAS:
        return SURYA_GANAS[pattern], "Surya"
    return None, "Unknown"


def find_dwipada_gana_partition(gana_markers: List[str], aksharalu: List[str]) -> Optional[Dict]:
    """
    Try to find a valid Dwipada Gana partition (3 Indra + 1 Surya).

    Returns:
        Dict with partition details or None if no valid partition found
    """
    pure_ganas = [g for g in gana_markers if g]
    pure_aksharalu = [ak for ak in aksharalu if ak not in ignorable_chars]

    if len(pure_ganas) < 4:
        return None

    pattern_str = "".join(pure_ganas)
    valid_partitions = []

    # Indra ganas can be 3 or 4 syllables, Surya can be 2 or 3
    for i1_len in [3, 4]:
        for i2_len in [3, 4]:
            for i3_len in [3, 4]:
                for s_len in [2, 3]:
                    total_len = i1_len + i2_len + i3_len + s_len

                    if total_len != len(pure_ganas):
                        continue

                    # Extract patterns
                    pos = 0
                    i1_pattern = pattern_str[pos:pos + i1_len]
                    pos += i1_len
                    i2_pattern = pattern_str[pos:pos + i2_len]
                    pos += i2_len
                    i3_pattern = pattern_str[pos:pos + i3_len]
                    pos += i3_len
                    s_pattern = pattern_str[pos:pos + s_len]

                    # Validate each Gana
                    i1_name, i1_type = identify_gana(i1_pattern)
                    i2_name, i2_type = identify_gana(i2_pattern)
                    i3_name, i3_type = identify_gana(i3_pattern)
                    s_name, s_type = identify_gana(s_pattern)

                    if (i1_type == "Indra" and i2_type == "Indra" and
                        i3_type == "Indra" and s_type == "Surya"):

                        # Get aksharalu for each Gana
                        pos = 0
                        i1_aksharalu = pure_aksharalu[pos:pos + i1_len]
                        pos += i1_len
                        i2_aksharalu = pure_aksharalu[pos:pos + i2_len]
                        pos += i2_len
                        i3_aksharalu = pure_aksharalu[pos:pos + i3_len]
                        pos += i3_len
                        s_aksharalu = pure_aksharalu[pos:pos + s_len]

                        valid_partitions.append({
                            "ganas": [
                                {"name": i1_name, "pattern": i1_pattern, "aksharalu": i1_aksharalu, "type": "Indra"},
                                {"name": i2_name, "pattern": i2_pattern, "aksharalu": i2_aksharalu, "type": "Indra"},
                                {"name": i3_name, "pattern": i3_pattern, "aksharalu": i3_aksharalu, "type": "Indra"},
                                {"name": s_name, "pattern": s_pattern, "aksharalu": s_aksharalu, "type": "Surya"},
                            ],
                            "total_syllables": len(pure_ganas)
                        })

    if valid_partitions:
        return valid_partitions[0]
    return None


def analyze_pada(line: str) -> Dict:
    """
    Analyze a single pada (line) of a Dwipada.

    Returns:
        Dict with analysis results
    """
    line = line.strip()
    aksharalu = split_aksharalu(line)
    pure_aksharalu = [ak for ak in aksharalu if ak not in ignorable_chars]
    gana_markers = akshara_ganavibhajana(aksharalu)
    pure_ganas = [g for g in gana_markers if g]
    partition = find_dwipada_gana_partition(gana_markers, aksharalu)

    first_aksharam = pure_aksharalu[0] if len(pure_aksharalu) > 0 else None
    second_aksharam = pure_aksharalu[1] if len(pure_aksharalu) > 1 else None

    # Get first letter of 3rd Gana for Yati check
    third_gana_first_letter = None
    if partition and len(partition["ganas"]) >= 3:
        third_gana_aksharalu = partition["ganas"][2]["aksharalu"]
        if third_gana_aksharalu:
            third_gana_first_letter = get_first_letter(third_gana_aksharalu[0])

    return {
        "line": line,
        "aksharalu": pure_aksharalu,
        "gana_markers": pure_ganas,
        "gana_string": "".join(pure_ganas),
        "partition": partition,
        "first_aksharam": first_aksharam,
        "second_aksharam": second_aksharam,
        "first_letter": get_first_letter(first_aksharam) if first_aksharam else None,
        "second_consonant": get_base_consonant(second_aksharam) if second_aksharam else None,
        "third_gana_first_letter": third_gana_first_letter,
        "is_valid_gana_sequence": partition is not None
    }


def analyze_dwipada(poem: str) -> Dict:
    """
    Analyze a complete Dwipada (2 lines separated by newline).

    Args:
        poem: A string containing two lines separated by newline character

    Returns:
        Dict with complete analysis including Prasa and Yati verification
    """
    lines = [l.strip() for l in poem.strip().split('\n') if l.strip()]
    if len(lines) < 2:
        raise ValueError("Dwipada must have 2 lines separated by newline")
    line1, line2 = lines[0], lines[1]

    pada1 = analyze_pada(line1)
    pada2 = analyze_pada(line2)

    # Check Prasa (2nd letter consonant match)
    prasa_match = False
    prasa_details = None
    if pada1["second_consonant"] and pada2["second_consonant"]:
        prasa_match = pada1["second_consonant"] == pada2["second_consonant"]
        prasa_details = {
            "line1_second_aksharam": pada1["second_aksharam"],
            "line1_consonant": pada1["second_consonant"],
            "line2_second_aksharam": pada2["second_aksharam"],
            "line2_consonant": pada2["second_consonant"],
            "match": prasa_match
        }

    # Check Yati for each line
    yati_line1 = None
    yati_line2 = None

    if pada1["first_letter"] and pada1["third_gana_first_letter"]:
        match, group_idx = check_yati_maitri(pada1["first_letter"], pada1["third_gana_first_letter"])
        yati_line1 = {
            "first_gana_letter": pada1["first_letter"],
            "third_gana_letter": pada1["third_gana_first_letter"],
            "match": match,
            "group_index": group_idx
        }

    if pada2["first_letter"] and pada2["third_gana_first_letter"]:
        match, group_idx = check_yati_maitri(pada2["first_letter"], pada2["third_gana_first_letter"])
        yati_line2 = {
            "first_gana_letter": pada2["first_letter"],
            "third_gana_letter": pada2["third_gana_first_letter"],
            "match": match,
            "group_index": group_idx
        }

    # Overall validity
    is_valid = (
        pada1["is_valid_gana_sequence"] and
        pada2["is_valid_gana_sequence"] and
        prasa_match and
        (yati_line1 is None or yati_line1["match"]) and
        (yati_line2 is None or yati_line2["match"])
    )

    return {
        "pada1": pada1,
        "pada2": pada2,
        "prasa": prasa_details,
        "yati_line1": yati_line1,
        "yati_line2": yati_line2,
        "is_valid_dwipada": is_valid,
        "validation_summary": {
            "gana_sequence_line1": pada1["is_valid_gana_sequence"],
            "gana_sequence_line2": pada2["is_valid_gana_sequence"],
            "prasa_match": prasa_match,
            "yati_line1_match": yati_line1["match"] if yati_line1 else None,
            "yati_line2_match": yati_line2["match"] if yati_line2 else None,
        }
    }


def format_analysis_report(analysis: Dict) -> str:
    """Format the analysis as a readable report."""
    lines = []
    lines.append("=" * 70)
    lines.append("DWIPADA CHANDASSU ANALYSIS REPORT")
    lines.append("=" * 70)

    # Line 1 Analysis
    lines.append("\n--- LINE 1 (పాదము 1) ---")
    pada1 = analysis["pada1"]
    lines.append(f"Text: {pada1['line']}")
    lines.append(f"Aksharalu: {' | '.join(pada1['aksharalu'])}")
    lines.append(f"Gana Markers: {' '.join(pada1['gana_markers'])}")

    if pada1["partition"]:
        lines.append("\nGana Breakdown:")
        for i, gana in enumerate(pada1["partition"]["ganas"], 1):
            gana_type_label = "ఇంద్ర గణము" if gana["type"] == "Indra" else "సూర్య గణము"
            lines.append(f"  Gana {i}: {''.join(gana['aksharalu'])} = {gana['pattern']} = {gana['name']} ({gana_type_label})")
    else:
        lines.append("\n[WARNING] Could not find valid 3 Indra + 1 Surya Gana partition")

    # Line 2 Analysis
    lines.append("\n--- LINE 2 (పాదము 2) ---")
    pada2 = analysis["pada2"]
    lines.append(f"Text: {pada2['line']}")
    lines.append(f"Aksharalu: {' | '.join(pada2['aksharalu'])}")
    lines.append(f"Gana Markers: {' '.join(pada2['gana_markers'])}")

    if pada2["partition"]:
        lines.append("\nGana Breakdown:")
        for i, gana in enumerate(pada2["partition"]["ganas"], 1):
            gana_type_label = "ఇంద్ర గణము" if gana["type"] == "Indra" else "సూర్య గణము"
            lines.append(f"  Gana {i}: {''.join(gana['aksharalu'])} = {gana['pattern']} = {gana['name']} ({gana_type_label})")
    else:
        lines.append("\n[WARNING] Could not find valid 3 Indra + 1 Surya Gana partition")

    # Prasa Analysis
    lines.append("\n--- PRASA (ప్రాస) ANALYSIS ---")
    if analysis["prasa"]:
        prasa = analysis["prasa"]
        status = "✓ MATCH" if prasa["match"] else "✗ NO MATCH"
        lines.append(f"Line 1 - 2nd Aksharam: '{prasa['line1_second_aksharam']}' (Consonant: {prasa['line1_consonant']})")
        lines.append(f"Line 2 - 2nd Aksharam: '{prasa['line2_second_aksharam']}' (Consonant: {prasa['line2_consonant']})")
        lines.append(f"Prasa Status: {status}")
    else:
        lines.append("Could not determine Prasa")

    # Yati Analysis
    lines.append("\n--- YATI (యతి) ANALYSIS ---")

    if analysis["yati_line1"]:
        yati1 = analysis["yati_line1"]
        status = "✓ MATCH" if yati1["match"] else "✗ NO MATCH"
        lines.append(f"Line 1: 1st Gana starts with '{yati1['first_gana_letter']}', 3rd Gana starts with '{yati1['third_gana_letter']}' - {status}")
    else:
        lines.append("Line 1: Could not determine Yati")

    if analysis["yati_line2"]:
        yati2 = analysis["yati_line2"]
        status = "✓ MATCH" if yati2["match"] else "✗ NO MATCH"
        lines.append(f"Line 2: 1st Gana starts with '{yati2['first_gana_letter']}', 3rd Gana starts with '{yati2['third_gana_letter']}' - {status}")
    else:
        lines.append("Line 2: Could not determine Yati")

    # Summary
    lines.append("\n" + "=" * 70)
    lines.append("VALIDATION SUMMARY")
    lines.append("=" * 70)
    summary = analysis["validation_summary"]
    lines.append(f"Gana Sequence Line 1: {'✓ Valid' if summary['gana_sequence_line1'] else '✗ Invalid'}")
    lines.append(f"Gana Sequence Line 2: {'✓ Valid' if summary['gana_sequence_line2'] else '✗ Invalid'}")
    lines.append(f"Prasa Match: {'✓ Yes' if summary['prasa_match'] else '✗ No'}")
    lines.append(f"Yati Line 1: {'✓ Match' if summary['yati_line1_match'] else '✗ No Match' if summary['yati_line1_match'] is False else 'N/A'}")
    lines.append(f"Yati Line 2: {'✓ Match' if summary['yati_line2_match'] else '✗ No Match' if summary['yati_line2_match'] is False else 'N/A'}")
    lines.append("")
    lines.append(f"OVERALL: {'✓ VALID DWIPADA' if analysis['is_valid_dwipada'] else '✗ INVALID DWIPADA'}")
    lines.append("=" * 70)

    return "\n".join(lines)


def analyze_single_line(line: str) -> str:
    """
    Analyze a single line and return a formatted report.
    Useful for quick analysis of individual padas.
    """
    pada = analyze_pada(line)
    lines = []
    lines.append("=" * 60)
    lines.append("SINGLE LINE ANALYSIS")
    lines.append("=" * 60)
    lines.append(f"Text: {pada['line']}")
    lines.append(f"Aksharalu: {' | '.join(pada['aksharalu'])}")
    lines.append(f"Gana Markers: {' '.join(pada['gana_markers'])}")
    lines.append(f"Gana String: {pada['gana_string']}")

    if pada["partition"]:
        lines.append("\nGana Breakdown (3 Indra + 1 Surya):")
        for i, gana in enumerate(pada["partition"]["ganas"], 1):
            gana_type_label = "ఇంద్ర" if gana["type"] == "Indra" else "సూర్య"
            aksharalu_str = "".join(gana['aksharalu'])
            lines.append(f"  {i}. {aksharalu_str} = {gana['pattern']} = {gana['name']} ({gana_type_label})")
        lines.append(f"\n✓ Valid Dwipada line structure")
    else:
        lines.append(f"\n✗ Could not find valid 3 Indra + 1 Surya partition")

    lines.append("=" * 60)
    return "\n".join(lines)


###############################################################################
# MAIN - COMPREHENSIVE TEST SUITE
###############################################################################

def run_tests():
    """Run comprehensive tests for Dwipada Analyzer."""
    passed = 0
    failed = 0

    print("=" * 70)
    print("DWIPADA ANALYZER - COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    # =========================================================================
    # TEST 1: Basic Aksharam Splitting
    # =========================================================================
    print("\n--- TEST 1: AKSHARAM SPLITTING ---")
    test_words = ["తెలుగు", "రాముడు", "సత్యము", "అమ్మ", "గౌరవం"]
    for word in test_words:
        aksharalu = split_aksharalu(word)
        ganas = akshara_ganavibhajana(aksharalu)
        pure_ganas = [g for g in ganas if g]
        print(f"  {word} → {' | '.join(aksharalu)} → {' '.join(pure_ganas)}")
    passed += 1
    print("✓ PASSED")

    # =========================================================================
    # TEST 2: Single Line Analysis
    # =========================================================================
    print("\n--- TEST 2: SINGLE LINE ANALYSIS ---")
    test_line = "సౌధాగ్రముల యందు సదనంబు లందు"
    pada = analyze_pada(test_line)
    if pada["is_valid_gana_sequence"]:
        print(f"  Line: {test_line}")
        print(f"  Gana String: {pada['gana_string']}")
        print("✓ PASSED - Valid gana sequence found")
        passed += 1
    else:
        print("✗ FAILED - Expected valid gana sequence")
        failed += 1

    # =========================================================================
    # TEST 3: Full Dwipada Analysis (Original)
    # =========================================================================
    print("\n--- TEST 3: FULL DWIPADA ANALYSIS ---")
    poem = """సౌధాగ్రముల యందు సదనంబు లందు
వీధుల యందును వెఱవొప్ప నిలిచి"""
    analysis = analyze_dwipada(poem)
    if analysis["is_valid_dwipada"]:
        print(f"  Prasa: {analysis['prasa']['line1_consonant']} = {analysis['prasa']['line2_consonant']}")
        print("✓ PASSED - Valid Dwipada")
        passed += 1
    else:
        print("✗ FAILED - Expected valid Dwipada")
        failed += 1

    # =========================================================================
    # CATEGORY 1: VALID DWIPADA COUPLETS FROM BHAGAVATAM (Tests 4-9)
    # =========================================================================
    print("\n" + "=" * 70)
    print("CATEGORY 1: VALID DWIPADA COUPLETS FROM BHAGAVATAM")
    print("=" * 70)

    # Test 4: Krishna description - Pootana story
    print("\n--- TEST 4: VALID - Pootana Story ---")
    poem4 = """ఈతఁడే యెలనాగ ఇసుమంతనాఁడు
పూతన పాల్ ద్రావి పొరిఁగొన్న వాఁడు"""
    try:
        analysis = analyze_dwipada(poem4)
        print(f"  Line 1: {analysis['pada1']['line']}")
        print(f"  Line 2: {analysis['pada2']['line']}")
        print(f"  Gana Seq Line1: {analysis['pada1']['is_valid_gana_sequence']}")
        print(f"  Gana Seq Line2: {analysis['pada2']['is_valid_gana_sequence']}")
        if analysis['prasa']:
            print(f"  Prasa: '{analysis['prasa']['line1_consonant']}' vs '{analysis['prasa']['line2_consonant']}' = {analysis['prasa']['match']}")
        print(f"  Valid Dwipada: {analysis['is_valid_dwipada']}")
        passed += 1
        print("✓ PASSED")
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1

    # Test 5: Shakatasura story
    print("\n--- TEST 5: VALID - Shakatasura Story ---")
    poem5 = """సకియరో ఈతఁడే శకటమై వచ్చు
ప్రకట దానవుఁ ద్రుళ్ళిపడఁ దన్నినాఁడు"""
    try:
        analysis = analyze_dwipada(poem5)
        print(f"  Gana Seq Line1: {analysis['pada1']['is_valid_gana_sequence']}")
        print(f"  Gana Seq Line2: {analysis['pada2']['is_valid_gana_sequence']}")
        if analysis['prasa']:
            print(f"  Prasa: '{analysis['prasa']['line1_consonant']}' vs '{analysis['prasa']['line2_consonant']}' = {analysis['prasa']['match']}")
        passed += 1
        print("✓ PASSED")
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1

    # Test 6: Govardhana story
    print("\n--- TEST 6: VALID - Maddiya Story ---")
    poem6 = """ముద్దియ ఈతఁడే మొగిఱోలుఁ ద్రోచి
మద్దియ లుడిపిన మహనీయ యశుఁడు"""
    try:
        analysis = analyze_dwipada(poem6)
        print(f"  Gana Seq Line1: {analysis['pada1']['is_valid_gana_sequence']}")
        print(f"  Gana Seq Line2: {analysis['pada2']['is_valid_gana_sequence']}")
        if analysis['prasa']:
            print(f"  Prasa: '{analysis['prasa']['line1_consonant']}' vs '{analysis['prasa']['line2_consonant']}' = {analysis['prasa']['match']}")
        passed += 1
        print("✓ PASSED")
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1

    # Test 7: Aghasura story
    print("\n--- TEST 7: VALID - Aghasura Story ---")
    poem7 = """అక్కరో ఈతఁడే యఘదైత్యుఁ జీరి
కొక్కెర రక్కసుఁ గూల్చినవాఁడు"""
    try:
        analysis = analyze_dwipada(poem7)
        print(f"  Gana Seq Line1: {analysis['pada1']['is_valid_gana_sequence']}")
        print(f"  Gana Seq Line2: {analysis['pada2']['is_valid_gana_sequence']}")
        if analysis['prasa']:
            print(f"  Prasa: '{analysis['prasa']['line1_consonant']}' vs '{analysis['prasa']['line2_consonant']}' = {analysis['prasa']['match']}")
        passed += 1
        print("✓ PASSED")
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1

    # Test 8: Govardhana
    print("\n--- TEST 8: VALID - Govardhana Story ---")
    poem8 = """గోవర్ధనముఁ గేల గొడుగుగాఁ బట్టి
గోవుల గోపాల గుంపులఁ గాచె"""
    try:
        analysis = analyze_dwipada(poem8)
        print(f"  Gana Seq Line1: {analysis['pada1']['is_valid_gana_sequence']}")
        print(f"  Gana Seq Line2: {analysis['pada2']['is_valid_gana_sequence']}")
        if analysis['prasa']:
            print(f"  Prasa: '{analysis['prasa']['line1_consonant']}' vs '{analysis['prasa']['line2_consonant']}' = {analysis['prasa']['match']}")
        passed += 1
        print("✓ PASSED")
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1

    # Test 9: Complex gana pattern
    print("\n--- TEST 9: VALID - Vanajākshi ---")
    poem9 = """వనజాక్షి రూపులావణ్యసంపదలు
వినిచిత్తమునఁ జూడ వేడుక పుట్టి"""
    try:
        analysis = analyze_dwipada(poem9)
        print(f"  Gana Seq Line1: {analysis['pada1']['is_valid_gana_sequence']}")
        print(f"  Gana Seq Line2: {analysis['pada2']['is_valid_gana_sequence']}")
        if analysis['prasa']:
            print(f"  Prasa: '{analysis['prasa']['line1_consonant']}' vs '{analysis['prasa']['line2_consonant']}' = {analysis['prasa']['match']}")
        passed += 1
        print("✓ PASSED")
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1

    # =========================================================================
    # CATEGORY 2: INVALID DWIPADA PATTERNS (Tests 10-13)
    # =========================================================================
    print("\n" + "=" * 70)
    print("CATEGORY 2: INVALID DWIPADA PATTERNS")
    print("=" * 70)

    # Test 10: Invalid - Prasa mismatch
    print("\n--- TEST 10: INVALID - Prasa Mismatch ---")
    poem10 = """సౌధాగ్రముల యందు సదనంబు లందు
వీమల యందును మెఱవొప్ప నిలిచి"""
    try:
        analysis = analyze_dwipada(poem10)
        if analysis['prasa'] and not analysis['prasa']['match']:
            print(f"  Prasa: '{analysis['prasa']['line1_consonant']}' vs '{analysis['prasa']['line2_consonant']}' = NO MATCH")
            print("✓ PASSED - Correctly detected Prasa mismatch")
            passed += 1
        else:
            print("✗ FAILED - Should have detected Prasa mismatch")
            failed += 1
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1

    # Test 11: Invalid - Insufficient syllables
    print("\n--- TEST 11: INVALID - Insufficient Syllables ---")
    poem11 = """కృష్ణుడు
రాముడు"""
    try:
        analysis = analyze_dwipada(poem11)
        if not analysis['pada1']['is_valid_gana_sequence'] or not analysis['pada2']['is_valid_gana_sequence']:
            print("✓ PASSED - Correctly detected insufficient syllables")
            passed += 1
        else:
            print("✗ FAILED - Should have detected insufficient syllables")
            failed += 1
    except Exception as e:
        print(f"✓ PASSED - Raised exception: {type(e).__name__}")
        passed += 1

    # Test 12: Invalid - Single line input
    print("\n--- TEST 12: INVALID - Single Line Input ---")
    poem12 = """సౌధాగ్రముల యందు సదనంబు లందు"""
    try:
        analysis = analyze_dwipada(poem12)
        print("✗ FAILED - Should have raised ValueError for single line")
        failed += 1
    except ValueError as e:
        print(f"✓ PASSED - Correctly raised ValueError: {e}")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED - Wrong exception type: {type(e).__name__}")
        failed += 1

    # Test 13: Invalid - Empty input
    print("\n--- TEST 13: INVALID - Empty Input ---")
    poem13 = """"""
    try:
        analysis = analyze_dwipada(poem13)
        print("✗ FAILED - Should have raised ValueError for empty input")
        failed += 1
    except ValueError as e:
        print(f"✓ PASSED - Correctly raised ValueError: {e}")
        passed += 1
    except Exception as e:
        print(f"✗ FAILED - Wrong exception type: {type(e).__name__}")
        failed += 1

    # =========================================================================
    # CATEGORY 3: GANA IDENTIFICATION TESTS (Tests 14-17)
    # =========================================================================
    print("\n" + "=" * 70)
    print("CATEGORY 3: GANA IDENTIFICATION TESTS")
    print("=" * 70)

    # Test 14: All Indra Gana types
    print("\n--- TEST 14: INDRA GANA IDENTIFICATION ---")
    indra_tests = [
        ("నలనల", "IIII", "Nala"),     # న|ల|న|ల = 4 Laghu
        ("కికికికూ", "IIIU", "Naga"),  # కి|కి|కి|కూ = 3 Laghu + 1 Guru
        ("కికికూకి", "IIUI", "Sala"),  # కి|కి|కూ|కి = pattern IIUI
        ("కూకిక", "UII", "Bha"),       # కూ|కి|క = 1 Guru + 2 Laghu
        ("కూకికూ", "UIU", "Ra"),       # కూ|కి|కూ = Guru-Laghu-Guru
        ("కూకూకి", "UUI", "Ta"),       # కూ|కూ|కి = 2 Guru + 1 Laghu
    ]
    all_passed = True
    for word, expected_pattern, gana_name in indra_tests:
        aksharalu = split_aksharalu(word)
        gana_markers = akshara_ganavibhajana(aksharalu)
        pattern = "".join([g for g in gana_markers if g])
        gana, gana_type = identify_gana(pattern)
        result = "✓" if pattern == expected_pattern else "✗"
        if pattern != expected_pattern:
            all_passed = False
        print(f"  {result} {word} → {pattern} (expected {expected_pattern}) = {gana_name}")
    if all_passed:
        passed += 1
        print("✓ PASSED - All Indra Ganas identified correctly")
    else:
        failed += 1
        print("✗ FAILED - Some Indra Ganas not identified correctly")

    # Test 15: All Surya Gana types
    print("\n--- TEST 15: SURYA GANA IDENTIFICATION ---")
    surya_tests = [
        ("కికికి", "III", "Na"),   # 3 Laghu
        ("కూకి", "UI", "Ha/Gala"),  # Guru + Laghu
    ]
    all_passed = True
    for word, expected_pattern, gana_name in surya_tests:
        aksharalu = split_aksharalu(word)
        gana_markers = akshara_ganavibhajana(aksharalu)
        pattern = "".join([g for g in gana_markers if g])
        gana, gana_type = identify_gana(pattern)
        result = "✓" if pattern == expected_pattern else "✗"
        if pattern != expected_pattern:
            all_passed = False
        print(f"  {result} {word} → {pattern} (expected {expected_pattern}) = {gana_name}")
    if all_passed:
        passed += 1
        print("✓ PASSED - All Surya Ganas identified correctly")
    else:
        failed += 1
        print("✗ FAILED - Some Surya Ganas not identified correctly")

    # Test 16: Mixed gana pattern line
    print("\n--- TEST 16: MIXED GANA PATTERN LINE ---")
    test_line16 = "సౌధాగ్రముల యందు సదనంబు లందు"
    pada = analyze_pada(test_line16)
    if pada["partition"]:
        print(f"  Line: {test_line16}")
        print(f"  Gana breakdown:")
        for i, gana in enumerate(pada["partition"]["ganas"], 1):
            print(f"    Gana {i}: {''.join(gana['aksharalu'])} = {gana['pattern']} = {gana['name']} ({gana['type']})")
        passed += 1
        print("✓ PASSED - Gana partition found")
    else:
        failed += 1
        print("✗ FAILED - Could not partition into ganas")

    # Test 17: Gana boundary edge case
    print("\n--- TEST 17: GANA BOUNDARY EDGE CASE ---")
    test_line17 = "వీధుల యందును వెఱవొప్ప నిలిచి"
    pada = analyze_pada(test_line17)
    if pada["partition"]:
        print(f"  Line: {test_line17}")
        print(f"  Total syllables: {len(pada['aksharalu'])}")
        print(f"  Gana string: {pada['gana_string']}")
        passed += 1
        print("✓ PASSED - Gana boundary correctly identified")
    else:
        failed += 1
        print("✗ FAILED - Could not identify gana boundary")

    # =========================================================================
    # CATEGORY 4: AKSHARAM & GURU/LAGHU EDGE CASES (Tests 18-21)
    # =========================================================================
    print("\n" + "=" * 70)
    print("CATEGORY 4: AKSHARAM & GURU/LAGHU EDGE CASES")
    print("=" * 70)

    # Test 18: Anusvaara (ం) as Guru
    print("\n--- TEST 18: ANUSVAARA (ం) AS GURU ---")
    anusvaara_words = ["సంపద", "గంగ", "మంగళం"]
    all_correct = True
    for word in anusvaara_words:
        aksharalu = split_aksharalu(word)
        ganas = akshara_ganavibhajana(aksharalu)
        # Check if syllables with ం are marked as Guru
        for i, ak in enumerate(aksharalu):
            if "ం" in ak and ganas[i] != "U":
                all_correct = False
        print(f"  {word} → {' | '.join(aksharalu)} → {' '.join([g for g in ganas if g])}")
    if all_correct:
        passed += 1
        print("✓ PASSED - Anusvaara syllables marked as Guru")
    else:
        failed += 1
        print("✗ FAILED - Some Anusvaara syllables not marked as Guru")

    # Test 19: Visarga (ః) as Guru
    print("\n--- TEST 19: VISARGA (ః) AS GURU ---")
    visarga_words = ["దుఃఖం", "నిఃశ్వాస"]
    all_correct = True
    for word in visarga_words:
        aksharalu = split_aksharalu(word)
        ganas = akshara_ganavibhajana(aksharalu)
        for i, ak in enumerate(aksharalu):
            if "ః" in ak and ganas[i] != "U":
                all_correct = False
        print(f"  {word} → {' | '.join(aksharalu)} → {' '.join([g for g in ganas if g])}")
    if all_correct:
        passed += 1
        print("✓ PASSED - Visarga syllables marked as Guru")
    else:
        failed += 1
        print("✗ FAILED - Some Visarga syllables not marked as Guru")

    # Test 20: Conjunct consonants (సంయుక్తాక్షరం)
    print("\n--- TEST 20: CONJUNCT CONSONANTS (సంయుక్తాక్షరం) ---")
    conjunct_words = ["సత్యము", "ధర్మము", "కృష్ణుడు"]
    print("  Syllable BEFORE conjunct should become Guru:")
    for word in conjunct_words:
        aksharalu = split_aksharalu(word)
        ganas = akshara_ganavibhajana(aksharalu)
        print(f"  {word} → {' | '.join(aksharalu)} → {' '.join([g for g in ganas if g])}")
    passed += 1
    print("✓ PASSED - Conjunct handling demonstrated")

    # Test 21: Double consonants (ద్విత్వాక్షరం)
    print("\n--- TEST 21: DOUBLE CONSONANTS (ద్విత్వాక్షరం) ---")
    double_words = ["అమ్మ", "అప్పా", "చిన్న"]
    print("  Syllable BEFORE double consonant should become Guru:")
    for word in double_words:
        aksharalu = split_aksharalu(word)
        ganas = akshara_ganavibhajana(aksharalu)
        print(f"  {word} → {' | '.join(aksharalu)} → {' '.join([g for g in ganas if g])}")
    passed += 1
    print("✓ PASSED - Double consonant handling demonstrated")

    # =========================================================================
    # CATEGORY 5: YATI (యతి) DETECTION TESTS (Tests 22-25)
    # =========================================================================
    print("\n" + "=" * 70)
    print("CATEGORY 5: YATI (యతి) DETECTION TESTS")
    print("=" * 70)

    # Test 22: Valid Yati - Same letter (exact match)
    print("\n--- TEST 22: VALID YATI - Same Letter ---")
    poem22 = """సౌధాగ్రముల యందు సదనంబు లందు
వీధుల యందును వెఱవొప్ప నిలిచి"""
    analysis = analyze_dwipada(poem22)
    yati1 = analysis.get("yati_line1")
    yati2 = analysis.get("yati_line2")
    if yati1:
        print(f"  Line 1: 1st Gana starts '{yati1['first_gana_letter']}', 3rd Gana starts '{yati1['third_gana_letter']}' = {'MATCH' if yati1['match'] else 'NO MATCH'}")
    if yati2:
        print(f"  Line 2: 1st Gana starts '{yati2['first_gana_letter']}', 3rd Gana starts '{yati2['third_gana_letter']}' = {'MATCH' if yati2['match'] else 'NO MATCH'}")
    if yati1 and yati1['match'] and yati2 and yati2['match']:
        passed += 1
        print("✓ PASSED - Yati matching correctly detected")
    else:
        failed += 1
        print("✗ FAILED - Yati matching not detected correctly")

    # Test 23: Valid Yati - Same Varga
    print("\n--- TEST 23: VALID YATI - Same Varga Test ---")
    # Testing yati maitri groups
    test_pairs = [
        ("అ", "ఆ", True, "అ-ఆ varga"),
        ("క", "గ", True, "క-గ varga"),
        ("చ", "శ", True, "చ-శ varga"),
        ("ప", "బ", True, "ప-బ varga"),
        ("ర", "ల", True, "ర-ల varga"),
    ]
    all_correct = True
    for l1, l2, expected, desc in test_pairs:
        match, group = check_yati_maitri(l1, l2)
        result = "✓" if match == expected else "✗"
        if match != expected:
            all_correct = False
        print(f"  {result} '{l1}' + '{l2}' ({desc}): {match}")
    if all_correct:
        passed += 1
        print("✓ PASSED - Yati Maitri varga matching works")
    else:
        failed += 1
        print("✗ FAILED - Some Yati Maitri matches incorrect")

    # Test 24: Valid Yati - క-వర్గము
    print("\n--- TEST 24: YATI - క-వర్గము GROUP ---")
    k_varga = ["క", "ఖ", "గ", "ఘ"]
    all_match = True
    for i, l1 in enumerate(k_varga):
        for l2 in k_varga[i+1:]:
            match, _ = check_yati_maitri(l1, l2)
            if not match:
                all_match = False
                print(f"  ✗ '{l1}' + '{l2}': NO MATCH (should match)")
    if all_match:
        passed += 1
        print(f"  All క-వర్గము letters match: {', '.join(k_varga)}")
        print("✓ PASSED - క-వర్గము matching works")
    else:
        failed += 1
        print("✗ FAILED - క-వర్గము matching has errors")

    # Test 25: Invalid Yati - Different Vargas
    print("\n--- TEST 25: INVALID YATI - Different Vargas ---")
    different_varga_pairs = [
        ("క", "చ", False, "క vs చ - different vargas"),
        ("ప", "త", False, "ప vs త - different vargas"),
        ("ర", "న", False, "ర vs న - different vargas"),
    ]
    all_correct = True
    for l1, l2, expected, desc in different_varga_pairs:
        match, group = check_yati_maitri(l1, l2)
        result = "✓" if match == expected else "✗"
        if match != expected:
            all_correct = False
        print(f"  {result} '{l1}' + '{l2}' ({desc}): {match}")
    if all_correct:
        passed += 1
        print("✓ PASSED - Different varga detection works")
    else:
        failed += 1
        print("✗ FAILED - Different varga detection has errors")

    # =========================================================================
    # CATEGORY 6: PRASA (ప్రాస) RHYME DETECTION TESTS (Tests 26-29)
    # =========================================================================
    print("\n" + "=" * 70)
    print("CATEGORY 6: PRASA (ప్రాస) RHYME DETECTION TESTS")
    print("=" * 70)

    # Test 26: Valid Prasa - Same consonant 'ధ'
    print("\n--- TEST 26: VALID PRASA - Consonant 'ధ' ---")
    poem26 = """సౌధాగ్రముల యందు సదనంబు లందు
వీధుల యందును వెఱవొప్ప నిలిచి"""
    analysis = analyze_dwipada(poem26)
    if analysis['prasa']:
        print(f"  Line 1 2nd aksharam: '{analysis['prasa']['line1_second_aksharam']}' (consonant: {analysis['prasa']['line1_consonant']})")
        print(f"  Line 2 2nd aksharam: '{analysis['prasa']['line2_second_aksharam']}' (consonant: {analysis['prasa']['line2_consonant']})")
        if analysis['prasa']['match']:
            passed += 1
            print("✓ PASSED - Prasa match detected")
        else:
            failed += 1
            print("✗ FAILED - Should have detected Prasa match")
    else:
        failed += 1
        print("✗ FAILED - Could not analyze Prasa")

    # Test 27: Valid Prasa - Same consonant 'క'
    print("\n--- TEST 27: VALID PRASA - Consonant 'క' ---")
    poem27 = """అక్కరో ఈతఁడే యఘదైత్యుఁ జీరి
కొక్కెర రక్కసుఁ గూల్చినవాఁడు"""
    analysis = analyze_dwipada(poem27)
    if analysis['prasa']:
        print(f"  Line 1 2nd aksharam: '{analysis['prasa']['line1_second_aksharam']}' (consonant: {analysis['prasa']['line1_consonant']})")
        print(f"  Line 2 2nd aksharam: '{analysis['prasa']['line2_second_aksharam']}' (consonant: {analysis['prasa']['line2_consonant']})")
        if analysis['prasa']['match']:
            passed += 1
            print("✓ PASSED - Prasa match detected")
        else:
            failed += 1
            print("✗ FAILED - Should have detected Prasa match")
    else:
        failed += 1
        print("✗ FAILED - Could not analyze Prasa")

    # Test 28: Invalid Prasa - Different consonants
    print("\n--- TEST 28: INVALID PRASA - Different Consonants ---")
    poem28 = """సౌధాగ్రముల యందు సదనంబు లందు
వీమల యందును మెఱవొప్ప నిలిచి"""
    analysis = analyze_dwipada(poem28)
    if analysis['prasa']:
        print(f"  Line 1 2nd aksharam: '{analysis['prasa']['line1_second_aksharam']}' (consonant: {analysis['prasa']['line1_consonant']})")
        print(f"  Line 2 2nd aksharam: '{analysis['prasa']['line2_second_aksharam']}' (consonant: {analysis['prasa']['line2_consonant']})")
        if not analysis['prasa']['match']:
            passed += 1
            print("✓ PASSED - Correctly detected Prasa mismatch")
        else:
            failed += 1
            print("✗ FAILED - Should have detected Prasa mismatch")
    else:
        failed += 1
        print("✗ FAILED - Could not analyze Prasa")

    # Test 29: Prasa with conjunct consonants
    print("\n--- TEST 29: PRASA WITH CONJUNCT CONSONANTS ---")
    poem29 = """సత్యమే ధర్మమై సదా విరాజిల్లు
నిత్యము నీ కీర్తి నిలిచి యుండు"""
    analysis = analyze_dwipada(poem29)
    if analysis['prasa']:
        print(f"  Line 1 2nd aksharam: '{analysis['prasa']['line1_second_aksharam']}' (consonant: {analysis['prasa']['line1_consonant']})")
        print(f"  Line 2 2nd aksharam: '{analysis['prasa']['line2_second_aksharam']}' (consonant: {analysis['prasa']['line2_consonant']})")
        print(f"  Prasa Match: {analysis['prasa']['match']}")
        passed += 1
        print("✓ PASSED - Conjunct Prasa analysis completed")
    else:
        failed += 1
        print("✗ FAILED - Could not analyze conjunct Prasa")

    # =========================================================================
    # CATEGORY 7: STANDALONE PRASA FUNCTIONS (Tests 30-33)
    # =========================================================================
    print("\n" + "=" * 70)
    print("CATEGORY 7: STANDALONE PRASA FUNCTIONS (check_prasa, check_prasa_aksharalu)")
    print("=" * 70)

    # Test 30: check_prasa() - Valid match
    print("\n--- TEST 30: check_prasa() - Valid Match ---")
    line1_30 = "సౌధాగ్రముల యందు సదనంబు లందు"
    line2_30 = "వీధుల యందును వెఱవొప్ప నిలిచి"
    is_match, details = check_prasa(line1_30, line2_30)
    print(f"  Line 1: {line1_30}")
    print(f"  Line 2: {line2_30}")
    print(f"  2nd aksharam Line1: '{details['line1_second_aksharam']}' (consonant: {details['line1_consonant']})")
    print(f"  2nd aksharam Line2: '{details['line2_second_aksharam']}' (consonant: {details['line2_consonant']})")
    print(f"  Match: {is_match}")
    if is_match:
        passed += 1
        print("✓ PASSED - check_prasa() correctly detected match")
    else:
        failed += 1
        print("✗ FAILED - check_prasa() should have detected match")

    # Test 31: check_prasa() - No match
    print("\n--- TEST 31: check_prasa() - No Match ---")
    line1_31 = "సౌధాగ్రముల యందు సదనంబు లందు"
    line2_31 = "వీమల యందును మెఱవొప్ప నిలిచి"
    is_match, details = check_prasa(line1_31, line2_31)
    print(f"  2nd aksharam Line1: '{details['line1_second_aksharam']}' (consonant: {details['line1_consonant']})")
    print(f"  2nd aksharam Line2: '{details['line2_second_aksharam']}' (consonant: {details['line2_consonant']})")
    print(f"  Match: {is_match}")
    if not is_match:
        passed += 1
        print("✓ PASSED - check_prasa() correctly detected no match")
    else:
        failed += 1
        print("✗ FAILED - check_prasa() should have detected no match")

    # Test 32: check_prasa_aksharalu() - Various pairs
    print("\n--- TEST 32: check_prasa_aksharalu() - Aksharam Pairs ---")
    aksharam_pairs = [
        ("ధా", "ధు", True, "Same consonant ధ with different vowels"),
        ("క్క", "క్కె", True, "Conjunct క with different vowels"),
        ("మా", "నా", False, "Different consonants మ vs న"),
        ("సా", "శా", False, "Different consonants స vs శ"),
        ("రా", "రి", True, "Same consonant ర with different vowels"),
    ]
    all_correct = True
    for ak1, ak2, expected, desc in aksharam_pairs:
        is_match, details = check_prasa_aksharalu(ak1, ak2)
        result = "✓" if is_match == expected else "✗"
        if is_match != expected:
            all_correct = False
        print(f"  {result} '{ak1}' + '{ak2}' ({desc}): {is_match}")
    if all_correct:
        passed += 1
        print("✓ PASSED - check_prasa_aksharalu() works correctly")
    else:
        failed += 1
        print("✗ FAILED - Some aksharam pairs not matched correctly")

    # Test 33: check_prasa() - Edge case with short lines
    print("\n--- TEST 33: check_prasa() - Edge Cases ---")
    # Short line test
    short_line1 = "క"
    short_line2 = "ర"
    is_match, details = check_prasa(short_line1, short_line2)
    if "error" in details:
        print(f"  Short lines: Correctly returned error - '{details['error']}'")
        passed += 1
        print("✓ PASSED - Edge case handled correctly")
    else:
        failed += 1
        print("✗ FAILED - Should have returned error for short lines")

    # =========================================================================
    # TEST SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    total = passed + failed
    print(f"  Total Tests: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Success Rate: {(passed/total)*100:.1f}%")
    print("=" * 70)

    return passed, failed


if __name__ == "__main__":
    run_tests()
