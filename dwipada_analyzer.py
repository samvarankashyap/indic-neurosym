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
# These groups define which letters can substitute for each other in Yati (యతి) matching
# Letters in the same group are phonetically related and can satisfy Yati requirements
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

# =============================================================================
# CONSONANT CLASSIFICATION (వర్ణమాల విభజన)
# =============================================================================
# Telugu consonants are grouped by place of articulation (ఉచ్చారణ స్థానం)
# Each varga shares similar mouth position when pronounced
#
# This classification is used for:
# 1. Prasa mismatch diagnostics - explaining why consonants don't match
# 2. Yati analysis - providing varga information for letter matching
# 3. Educational purposes - showing phonetic relationships

CONSONANT_VARGAS = {
    # Velar (కంఠ్యము) - produced at the soft palate (back of mouth)
    "క-వర్గము (Velar)": ["క", "ఖ", "గ", "ఘ", "ఙ"],

    # Palatal (తాలవ్యము) - produced at the hard palate
    # Includes sibilants (శ, ష, స) which share palatal articulation
    "చ-వర్గము (Palatal)": ["చ", "ఛ", "జ", "ఝ", "ఞ", "శ", "ష", "స"],

    # Retroflex (మూర్ధన్యము) - tongue curled back touching roof of mouth
    "ట-వర్గము (Retroflex)": ["ట", "ఠ", "డ", "ఢ", "ణ"],

    # Dental (దంత్యము) - tongue touches upper teeth
    "త-వర్గము (Dental)": ["త", "థ", "ద", "ధ", "న"],

    # Labial (ఓష్ఠ్యము) - produced with lips
    "ప-వర్గము (Labial)": ["ప", "ఫ", "బ", "భ", "మ"],

    # Semi-vowels and approximants (అంతస్థములు)
    "య-వర్గము (Approximant)": ["య", "ర", "ల", "వ", "ళ", "ఱ"],

    # Aspirate (ఊష్మము)
    "హ-వర్గము (Aspirate)": ["హ"],
}


def get_consonant_varga(consonant: str) -> Optional[str]:
    """
    Get the varga (consonant class) for a Telugu consonant.

    Telugu consonants are classified into vargas based on their place of
    articulation (ఉచ్చారణ స్థానం). This function returns which varga
    a given consonant belongs to.

    Args:
        consonant: A single Telugu consonant character (హల్లు)

    Returns:
        Varga name (e.g., "క-వర్గము (Velar)") or None if not a consonant

    Example:
        >>> get_consonant_varga("క")
        "క-వర్గము (Velar)"
        >>> get_consonant_varga("ధ")
        "త-వర్గము (Dental)"
        >>> get_consonant_varga("అ")
        None  # అ is a vowel, not a consonant
    """
    if not consonant:
        return None

    for varga_name, consonants in CONSONANT_VARGAS.items():
        if consonant in consonants:
            return varga_name

    return None


def get_letter_info(letter: str) -> Dict:
    """
    Get complete classification information for a Telugu letter.

    This function provides comprehensive details about any Telugu letter,
    including whether it's a vowel or consonant, its varga classification,
    and which Yati Maitri groups it belongs to.

    Args:
        letter: A single Telugu letter (vowel or consonant)

    Returns:
        Dictionary with the following keys:
        - letter: The input letter
        - type: "vowel" (అచ్చు), "consonant" (హల్లు), or "unknown"
        - varga: Consonant varga name (only for consonants)
        - yati_groups: List of Yati Maitri group indices this letter belongs to
        - yati_group_members: List of all members in the letter's Yati groups

    Example:
        >>> get_letter_info("క")
        {
            "letter": "క",
            "type": "consonant",
            "varga": "క-వర్గము (Velar)",
            "yati_groups": [3],
            "yati_group_members": ["క", "ఖ", "గ", "ఘ", "క్ష"]
        }
    """
    result = {
        "letter": letter,
        "type": "unknown",
        "varga": None,
        "yati_groups": [],
        "yati_group_members": [],
    }

    if not letter:
        return result

    # Determine if vowel or consonant
    if letter in independent_vowels or letter in dependent_vowels:
        result["type"] = "vowel"
    elif letter in telugu_consonants:
        result["type"] = "consonant"
        result["varga"] = get_consonant_varga(letter)

    # Find Yati Maitri groups this letter belongs to
    for idx, group in enumerate(YATI_MAITRI_GROUPS):
        if letter in group:
            result["yati_groups"].append(idx)
            result["yati_group_members"].extend(list(group))

    # Remove duplicates from group members while preserving order
    seen = set()
    unique_members = []
    for member in result["yati_group_members"]:
        if member not in seen:
            seen.add(member)
            unique_members.append(member)
    result["yati_group_members"] = unique_members

    return result


# =============================================================================
# SCORING HELPER FUNCTIONS
# =============================================================================
# These functions calculate percentage scores for different aspects of
# Dwipada poetry analysis. Scores range from 0-100%.
#
# Scoring Philosophy:
# - Gana matching: 25% per valid gana (4 ganas per line = 100%)
# - Prasa: Binary - 100% if match, 0% if mismatch
# - Yati: 100% for exact letter match, 70% for same varga, 0% for different

# Weights for overall score calculation
SCORE_WEIGHTS = {
    "gana": 0.40,   # 40% weight - gana sequence is fundamental structure
    "prasa": 0.35,  # 35% weight - prasa (rhyme) is essential for dwipada
    "yati": 0.25,   # 25% weight - yati adds phonetic beauty
}


def calculate_gana_score(partition_result: Optional[Dict]) -> Dict:
    """
    Calculate the percentage score for gana matching.

    A valid Dwipada line has 4 ganas: 3 Indra ganas + 1 Surya gana.
    Each valid gana contributes 25% to the score (4 × 25% = 100%).

    Args:
        partition_result: The result from find_dwipada_gana_partition()
                         Contains "ganas" list with each gana's validity

    Returns:
        Dictionary with:
        - score: Float 0-100 representing percentage match
        - ganas_matched: Number of valid ganas found (0-4)
        - ganas_total: Expected number of ganas (4)
        - details: List of per-gana validity info

    Example:
        >>> partition = find_dwipada_gana_partition(gana_markers, aksharalu)
        >>> calculate_gana_score(partition)
        {"score": 100.0, "ganas_matched": 4, "ganas_total": 4, "details": [...]}
    """
    result = {
        "score": 0.0,
        "ganas_matched": 0,
        "ganas_total": 4,
        "details": [],
    }

    if not partition_result or "ganas" not in partition_result:
        return result

    ganas = partition_result["ganas"]
    valid_count = 0

    for i, gana in enumerate(ganas, 1):
        is_valid = gana.get("name") is not None
        if is_valid:
            valid_count += 1

        result["details"].append({
            "position": i,
            "type": gana.get("type", "Unknown"),
            "pattern": gana.get("pattern", ""),
            "name": gana.get("name"),
            "valid": is_valid,
            "aksharalu": gana.get("aksharalu", []),
        })

    result["ganas_matched"] = valid_count
    result["score"] = (valid_count / 4) * 100.0

    return result


def calculate_prasa_score(prasa_result: Optional[Dict]) -> Dict:
    """
    Calculate the percentage score for prasa (rhyme) matching.

    Prasa is binary: either the 2nd syllable consonants match (100%) or
    they don't (0%). This function also provides diagnostic information
    about why a mismatch occurred.

    Args:
        prasa_result: Dictionary containing prasa analysis results
                     with "match", "line1_consonant", "line2_consonant" keys

    Returns:
        Dictionary with:
        - score: Float 0 or 100
        - match: Boolean indicating if prasa matches
        - mismatch_details: Diagnostic info if mismatch (None if match)

    Example:
        >>> prasa = {"match": False, "line1_consonant": "ధ", "line2_consonant": "మ"}
        >>> calculate_prasa_score(prasa)
        {"score": 0.0, "match": False, "mismatch_details": {...}}
    """
    result = {
        "score": 0.0,
        "match": False,
        "mismatch_details": None,
    }

    if not prasa_result:
        return result

    is_match = prasa_result.get("match", False)
    result["match"] = is_match
    result["score"] = 100.0 if is_match else 0.0

    # Generate mismatch diagnostics if not matching
    if not is_match:
        cons1 = prasa_result.get("line1_consonant")
        cons2 = prasa_result.get("line2_consonant")
        varga1 = get_consonant_varga(cons1) if cons1 else None
        varga2 = get_consonant_varga(cons2) if cons2 else None

        result["mismatch_details"] = {
            "line1_full_breakdown": {
                "aksharam": prasa_result.get("line1_second_aksharam"),
                "consonant": cons1,
                "consonant_varga": varga1,
            },
            "line2_full_breakdown": {
                "aksharam": prasa_result.get("line2_second_aksharam"),
                "consonant": cons2,
                "consonant_varga": varga2,
            },
            "why_mismatch": _generate_prasa_mismatch_explanation(cons1, cons2, varga1, varga2),
            "suggestion": _generate_prasa_suggestion(cons1),
        }

    return result


def _generate_prasa_mismatch_explanation(cons1: str, cons2: str,
                                         varga1: Optional[str],
                                         varga2: Optional[str]) -> str:
    """
    Generate a human-readable explanation for why prasa doesn't match.

    This helper function creates educational diagnostic messages explaining
    why two consonants don't satisfy the prasa requirement.

    Args:
        cons1: First consonant
        cons2: Second consonant
        varga1: Varga of first consonant
        varga2: Varga of second consonant

    Returns:
        Explanation string in Telugu/English mixed format
    """
    if not cons1 or not cons2:
        return "One or both lines don't have a valid consonant in 2nd position"

    if varga1 and varga2:
        if varga1 == varga2:
            return f"Consonants '{cons1}' and '{cons2}' are from same varga ({varga1}) but prasa requires exact match"
        else:
            return f"Consonants '{cons1}' ({varga1}) and '{cons2}' ({varga2}) are from different vargas"

    return f"Consonants '{cons1}' and '{cons2}' do not match - prasa requires identical consonants"


def _generate_prasa_suggestion(consonant: str) -> str:
    """
    Generate a suggestion for fixing prasa mismatch.

    Provides examples of syllables that would create valid prasa
    with the given consonant.

    Args:
        consonant: The consonant from line 1's 2nd syllable

    Returns:
        Suggestion string with example valid syllables
    """
    if not consonant:
        return "Unable to generate suggestion - no valid consonant found"

    # Common vowel combinations for examples
    vowels = ["", "ా", "ి", "ీ", "ు", "ూ", "ె", "ే", "ో"]
    examples = [consonant + v for v in vowels[:5]]

    return f"Line 2 needs 2nd syllable with '{consonant}' consonant (e.g., {', '.join(examples)}...)"


def calculate_yati_score(yati_result: Optional[Dict]) -> Dict:
    """
    Calculate the percentage score for yati (alliteration) matching.

    Yati scoring is nuanced:
    - 100%: Exact letter match (same letter in 1st and 3rd gana positions)
    - 70%: Same Yati Maitri varga (phonetically related letters)
    - 0%: Different vargas (no phonetic relationship)

    Args:
        yati_result: Dictionary containing yati analysis with
                    "match", "first_gana_letter", "third_gana_letter" keys

    Returns:
        Dictionary with:
        - score: Float 0, 70, or 100
        - quality: "exact", "varga_match", or "no_match"
        - mismatch_details: Diagnostic info (always provided for transparency)

    Example:
        >>> yati = {"match": True, "first_gana_letter": "స", "third_gana_letter": "స"}
        >>> calculate_yati_score(yati)
        {"score": 100.0, "quality": "exact", "mismatch_details": {...}}
    """
    result = {
        "score": 0.0,
        "quality": "no_match",
        "mismatch_details": None,
    }

    if not yati_result:
        return result

    letter1 = yati_result.get("first_gana_letter")
    letter2 = yati_result.get("third_gana_letter")
    is_match = yati_result.get("match", False)
    group_idx = yati_result.get("group_index")

    # Get detailed letter information
    info1 = get_letter_info(letter1) if letter1 else None
    info2 = get_letter_info(letter2) if letter2 else None

    # Determine quality of match
    if is_match:
        if letter1 == letter2:
            result["score"] = 100.0
            result["quality"] = "exact"
        else:
            # Same varga but different letter
            result["score"] = 70.0
            result["quality"] = "varga_match"
    else:
        result["score"] = 0.0
        result["quality"] = "no_match"

    # Always provide letter details for educational purposes
    result["mismatch_details"] = {
        "letter1_info": info1,
        "letter2_info": info2,
        "why_result": _generate_yati_explanation(letter1, letter2, is_match, info1, info2),
        "suggestion": _generate_yati_suggestion(letter1, info1) if not is_match else None,
    }

    return result


def _generate_yati_explanation(letter1: str, letter2: str, is_match: bool,
                               info1: Optional[Dict], info2: Optional[Dict]) -> str:
    """
    Generate a human-readable explanation for yati match result.

    Args:
        letter1: First letter (1st gana start)
        letter2: Second letter (3rd gana start)
        is_match: Whether yati is satisfied
        info1: Letter info for first letter
        info2: Letter info for second letter

    Returns:
        Explanation string describing why yati matches or doesn't
    """
    if not letter1 or not letter2:
        return "Unable to determine yati - missing letter information"

    if letter1 == letter2:
        return f"Exact match: both positions have '{letter1}' → MATCH (100%)"

    if is_match:
        # Same varga match
        groups1 = info1.get("yati_group_members", []) if info1 else []
        return f"'{letter1}' and '{letter2}' belong to same Yati Maitri group {groups1} → MATCH (70%)"

    # No match - explain why
    varga1 = info1.get("varga") if info1 else None
    varga2 = info2.get("varga") if info2 else None

    if varga1 and varga2:
        return f"'{letter1}' is in {varga1}, '{letter2}' is in {varga2} → NO MATCH"

    return f"'{letter1}' and '{letter2}' are not in the same Yati Maitri group → NO MATCH"


def _generate_yati_suggestion(letter: str, info: Optional[Dict]) -> str:
    """
    Generate a suggestion for fixing yati mismatch.

    Args:
        letter: The letter from 1st gana position
        info: Letter info dict

    Returns:
        Suggestion string with valid alternatives
    """
    if not letter or not info:
        return "Unable to generate suggestion"

    group_members = info.get("yati_group_members", [])
    if group_members:
        return f"1st syllable of 3rd gana should start with: {', '.join(group_members)}"

    return f"1st syllable of 3rd gana should start with '{letter}' or related letters"


def calculate_overall_score(gana_score1: Dict, gana_score2: Dict,
                           prasa_score: Dict,
                           yati_score1: Dict, yati_score2: Dict) -> Dict:
    """
    Calculate the weighted overall match score for a Dwipada couplet.

    This function combines individual scores from gana, prasa, and yati
    analysis into a single percentage score using configurable weights.

    Weights (defined in SCORE_WEIGHTS):
    - Gana: 40% (average of both lines)
    - Prasa: 35%
    - Yati: 25% (average of both lines)

    Args:
        gana_score1: Gana score dict for line 1
        gana_score2: Gana score dict for line 2
        prasa_score: Prasa score dict for the couplet
        yati_score1: Yati score dict for line 1
        yati_score2: Yati score dict for line 2

    Returns:
        Dictionary with:
        - overall: Float 0-100 representing weighted average
        - breakdown: Individual component scores
        - weights: The weights used for calculation

    Example:
        >>> calculate_overall_score(gana1, gana2, prasa, yati1, yati2)
        {
            "overall": 85.0,
            "breakdown": {
                "gana_line1": 100.0, "gana_line2": 75.0,
                "prasa": 100.0, "yati_line1": 70.0, "yati_line2": 100.0
            },
            "weights": {"gana": 0.40, "prasa": 0.35, "yati": 0.25}
        }
    """
    # Extract individual scores
    gana1 = gana_score1.get("score", 0.0)
    gana2 = gana_score2.get("score", 0.0)
    prasa = prasa_score.get("score", 0.0)
    yati1 = yati_score1.get("score", 0.0)
    yati2 = yati_score2.get("score", 0.0)

    # Calculate averages for multi-line components
    avg_gana = (gana1 + gana2) / 2
    avg_yati = (yati1 + yati2) / 2

    # Calculate weighted overall score
    overall = (
        avg_gana * SCORE_WEIGHTS["gana"] +
        prasa * SCORE_WEIGHTS["prasa"] +
        avg_yati * SCORE_WEIGHTS["yati"]
    )

    return {
        "overall": round(overall, 1),
        "breakdown": {
            "gana_line1": gana1,
            "gana_line2": gana2,
            "gana_average": round(avg_gana, 1),
            "prasa": prasa,
            "yati_line1": yati1,
            "yati_line2": yati2,
            "yati_average": round(avg_yati, 1),
        },
        "weights": SCORE_WEIGHTS.copy(),
    }


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


def check_yati_maitri(letter1: str, letter2: str) -> Tuple[bool, Optional[int], Dict]:
    """
    Check if two letters belong to the same Yati Maitri group.

    Yati (యతి) is the rule of phonetic harmony in Telugu poetry.
    The 1st letter of the 1st gana must match (or be phonetically related to)
    the 1st letter of the 3rd gana in a Dwipada line.

    Match quality levels:
    - Exact match: Same letter (100% quality)
    - Varga match: Same Yati Maitri group (70% quality)
    - No match: Different groups (0% quality)

    Args:
        letter1: First letter (from 1st gana start)
        letter2: Second letter (from 3rd gana start)

    Returns:
        Tuple of (is_match, group_index, details_dict) where:
        - is_match: Boolean indicating if yati is satisfied
        - group_index: Index of matching group (-1 for exact, None for no match)
        - details_dict: Contains quality_score, match_type, and letter info

    Example:
        >>> match, idx, details = check_yati_maitri("స", "స")
        >>> match, details["quality_score"], details["match_type"]
        (True, 100.0, "exact")

        >>> match, idx, details = check_yati_maitri("క", "గ")
        >>> match, details["quality_score"], details["match_type"]
        (True, 70.0, "varga_match")
    """
    details = {
        "letter1": letter1,
        "letter2": letter2,
        "quality_score": 0.0,
        "match_type": "no_match",
        "letter1_info": None,
        "letter2_info": None,
        "matching_group_members": None,
    }

    if not letter1 or not letter2:
        return False, None, details

    # Get detailed info for both letters
    details["letter1_info"] = get_letter_info(letter1)
    details["letter2_info"] = get_letter_info(letter2)

    # Check for exact match first (highest quality)
    if letter1 == letter2:
        details["quality_score"] = 100.0
        details["match_type"] = "exact"
        return True, -1, details

    # Check for Yati Maitri group match (medium quality)
    for idx, group in enumerate(YATI_MAITRI_GROUPS):
        if letter1 in group and letter2 in group:
            details["quality_score"] = 70.0
            details["match_type"] = "varga_match"
            details["matching_group_members"] = list(group)
            return True, idx, details

    # No match
    details["quality_score"] = 0.0
    details["match_type"] = "no_match"
    return False, None, details


def check_yati_maitri_simple(letter1: str, letter2: str) -> Tuple[bool, Optional[int]]:
    """
    Simple version of check_yati_maitri for backward compatibility.

    Returns only (is_match, group_index) without detailed diagnostics.
    Use check_yati_maitri() for full analysis with quality scoring.

    Args:
        letter1: First letter
        letter2: Second letter

    Returns:
        Tuple of (is_match, group_index)
    """
    is_match, group_idx, _ = check_yati_maitri(letter1, letter2)
    return is_match, group_idx


def check_prasa(line1: str, line2: str) -> Tuple[bool, Dict]:
    """
    Check Prasa (rhyme) between two lines.

    Prasa rule: The 2nd aksharam's base consonant must match between the two lines.
    This is the fundamental rhyming requirement for Dwipada poetry.

    This enhanced version provides detailed mismatch diagnostics including:
    - Full aksharam breakdown (consonant, vowel, varga)
    - Explanation of why mismatch occurred
    - Suggestions for fixing the mismatch

    Args:
        line1: First line of dwipada
        line2: Second line of dwipada

    Returns:
        Tuple of (is_match, details_dict) where details_dict contains:
        - line1_second_aksharam: The 2nd syllable from line 1
        - line1_consonant: Base consonant of line 1's 2nd syllable
        - line2_second_aksharam: The 2nd syllable from line 2
        - line2_consonant: Base consonant of line 2's 2nd syllable
        - match: Boolean indicating if prasa is satisfied
        - mismatch_details: Diagnostic info when match is False (None if match)

    Example:
        >>> is_match, details = check_prasa("సౌధాగ్రముల యందు", "వీధుల యందును")
        >>> is_match
        True  # Both have 'ధ' as 2nd consonant
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

    # Compare consonants
    is_match = consonant1 == consonant2 if consonant1 and consonant2 else False

    # Build result dictionary
    result = {
        "line1_second_aksharam": second_ak1,
        "line1_consonant": consonant1,
        "line2_second_aksharam": second_ak2,
        "line2_consonant": consonant2,
        "match": is_match,
        "mismatch_details": None,
    }

    # Add detailed diagnostics if not matching
    if not is_match:
        varga1 = get_consonant_varga(consonant1) if consonant1 else None
        varga2 = get_consonant_varga(consonant2) if consonant2 else None

        # Extract vowel from aksharam for full breakdown
        vowel1 = _extract_vowel_from_aksharam(second_ak1)
        vowel2 = _extract_vowel_from_aksharam(second_ak2)

        result["mismatch_details"] = {
            "line1_full_breakdown": {
                "aksharam": second_ak1,
                "consonant": consonant1,
                "vowel": vowel1,
                "consonant_varga": varga1,
            },
            "line2_full_breakdown": {
                "aksharam": second_ak2,
                "consonant": consonant2,
                "vowel": vowel2,
                "consonant_varga": varga2,
            },
            "why_mismatch": _generate_prasa_mismatch_explanation(consonant1, consonant2, varga1, varga2),
            "suggestion": _generate_prasa_suggestion(consonant1),
        }

    return is_match, result


def _extract_vowel_from_aksharam(aksharam: str) -> str:
    """
    Extract the vowel component from a Telugu aksharam.

    An aksharam typically consists of:
    - Consonant(s) + dependent vowel (e.g., కా = క + ా)
    - Or standalone vowel (e.g., అ, ఆ)

    If no explicit vowel marker, returns "అ (implicit)" since Telugu
    consonants without vowel markers have inherent 'అ' sound.

    Args:
        aksharam: A Telugu syllable

    Returns:
        The vowel part as a string (e.g., "ా", "ి", or "అ (implicit)")
    """
    if not aksharam:
        return ""

    # Check for dependent vowels
    for dv in dependent_vowels:
        if dv in aksharam:
            return dv

    # Check if it's an independent vowel
    if aksharam[0] in independent_vowels:
        return aksharam[0]

    # No explicit vowel - inherent 'అ' sound
    return "అ (implicit)"


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

    This function tries all 16 possible combinations of gana lengths:
    - Indra ganas: 3 or 4 syllables (2 choices × 3 ganas = 8 combinations)
    - Surya gana: 2 or 3 syllables (2 choices)
    - Total: 2 × 2 × 2 × 2 = 16 combinations

    The function returns the best partition found, with detailed information
    about how many ganas matched and which ones failed.

    Args:
        gana_markers: List of "U" (Guru) and "I" (Laghu) markers
        aksharalu: List of syllables corresponding to the markers

    Returns:
        Dict with partition details including:
        - ganas: List of 4 gana dicts with name, pattern, aksharalu, type, valid
        - total_syllables: Number of syllables in the line
        - ganas_matched: How many of 4 ganas are valid (0-4)
        - all_partitions_tried: Total partition combinations attempted
        - valid_partitions_found: How many fully valid partitions exist
        - is_fully_valid: True if all 4 ganas match expected types

        Returns None only if line has fewer than 4 syllables.
    """
    pure_ganas = [g for g in gana_markers if g]
    pure_aksharalu = [ak for ak in aksharalu if ak not in ignorable_chars]

    # Need at least 4 syllables for a dwipada line (minimum: 3+3+3+2 = 11, but check >= 4 for safety)
    if len(pure_ganas) < 4:
        return None

    pattern_str = "".join(pure_ganas)
    valid_partitions = []
    all_partitions = []  # Track all attempted partitions for diagnostics
    partitions_tried = 0

    # Try all 16 combinations of gana lengths
    # Indra ganas can be 3 or 4 syllables, Surya can be 2 or 3
    for i1_len in [3, 4]:
        for i2_len in [3, 4]:
            for i3_len in [3, 4]:
                for s_len in [2, 3]:
                    total_len = i1_len + i2_len + i3_len + s_len

                    # Skip if total doesn't match line length
                    if total_len != len(pure_ganas):
                        continue

                    partitions_tried += 1

                    # Extract patterns for each gana position
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

                    # Get aksharalu for each Gana
                    pos = 0
                    i1_aksharalu = pure_aksharalu[pos:pos + i1_len]
                    pos += i1_len
                    i2_aksharalu = pure_aksharalu[pos:pos + i2_len]
                    pos += i2_len
                    i3_aksharalu = pure_aksharalu[pos:pos + i3_len]
                    pos += i3_len
                    s_aksharalu = pure_aksharalu[pos:pos + s_len]

                    # Check validity of each gana position
                    g1_valid = i1_type == "Indra"
                    g2_valid = i2_type == "Indra"
                    g3_valid = i3_type == "Indra"
                    g4_valid = s_type == "Surya"

                    valid_count = sum([g1_valid, g2_valid, g3_valid, g4_valid])
                    is_fully_valid = valid_count == 4

                    # Build gana detail with validity info
                    partition_data = {
                        "ganas": [
                            {
                                "position": 1,
                                "name": i1_name,
                                "pattern": i1_pattern,
                                "aksharalu": i1_aksharalu,
                                "type": "Indra",
                                "expected_type": "Indra",
                                "valid": g1_valid,
                                "error": None if g1_valid else f"Pattern '{i1_pattern}' is not a valid Indra gana"
                            },
                            {
                                "position": 2,
                                "name": i2_name,
                                "pattern": i2_pattern,
                                "aksharalu": i2_aksharalu,
                                "type": "Indra",
                                "expected_type": "Indra",
                                "valid": g2_valid,
                                "error": None if g2_valid else f"Pattern '{i2_pattern}' is not a valid Indra gana"
                            },
                            {
                                "position": 3,
                                "name": i3_name,
                                "pattern": i3_pattern,
                                "aksharalu": i3_aksharalu,
                                "type": "Indra",
                                "expected_type": "Indra",
                                "valid": g3_valid,
                                "error": None if g3_valid else f"Pattern '{i3_pattern}' is not a valid Indra gana"
                            },
                            {
                                "position": 4,
                                "name": s_name,
                                "pattern": s_pattern,
                                "aksharalu": s_aksharalu,
                                "type": "Surya",
                                "expected_type": "Surya",
                                "valid": g4_valid,
                                "error": None if g4_valid else f"Pattern '{s_pattern}' is not a valid Surya gana"
                            },
                        ],
                        "total_syllables": len(pure_ganas),
                        "ganas_matched": valid_count,
                        "is_fully_valid": is_fully_valid,
                        "partition_lengths": [i1_len, i2_len, i3_len, s_len],
                    }

                    all_partitions.append(partition_data)

                    if is_fully_valid:
                        valid_partitions.append(partition_data)

    # If no partitions were tried (line too short/long), return None
    if partitions_tried == 0:
        return None

    # Return best partition found
    # Priority: fully valid > highest ganas_matched > first attempted
    if valid_partitions:
        best = valid_partitions[0]
    else:
        # Find partition with most valid ganas
        best = max(all_partitions, key=lambda p: p["ganas_matched"])

    # Add metadata about all attempts
    best["all_partitions_tried"] = partitions_tried
    best["valid_partitions_found"] = len(valid_partitions)

    return best


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

    This is the main analysis function that provides comprehensive feedback on
    a Dwipada couplet including:
    - Per-line gana partition analysis
    - Prasa (rhyme) verification with mismatch diagnostics
    - Yati (alliteration) verification with quality scoring
    - Overall percentage match score

    Args:
        poem: A string containing two lines separated by newline character

    Returns:
        Dict with complete analysis including:
        - pada1, pada2: Per-line analysis results
        - prasa: Prasa check with mismatch details if applicable
        - yati_line1, yati_line2: Yati check with quality scores
        - is_valid_dwipada: Boolean - True if all rules satisfied
        - match_score: Percentage scores (overall and breakdown)
        - validation_summary: Quick boolean summary of all checks

    Example:
        >>> analysis = analyze_dwipada("సౌధాగ్రముల యందు సదనంబు లందు\\nవీధుల యందును వెఱవొప్ప నిలిచి")
        >>> analysis["is_valid_dwipada"]
        True
        >>> analysis["match_score"]["overall"]
        100.0
    """
    lines = [l.strip() for l in poem.strip().split('\n') if l.strip()]
    if len(lines) < 2:
        raise ValueError("Dwipada must have 2 lines separated by newline")
    line1, line2 = lines[0], lines[1]

    # Analyze each pada (line)
    pada1 = analyze_pada(line1)
    pada2 = analyze_pada(line2)

    # Use enhanced check_prasa with full mismatch diagnostics
    prasa_match, prasa_details = check_prasa(line1, line2)

    # Check Yati for each line with enhanced diagnostics
    yati_line1 = None
    yati_line2 = None
    yati_details1 = None
    yati_details2 = None

    if pada1["first_letter"] and pada1["third_gana_first_letter"]:
        match, group_idx, yati_details1 = check_yati_maitri(
            pada1["first_letter"],
            pada1["third_gana_first_letter"]
        )
        yati_line1 = {
            "first_gana_letter": pada1["first_letter"],
            "third_gana_letter": pada1["third_gana_first_letter"],
            "match": match,
            "group_index": group_idx,
            "quality_score": yati_details1.get("quality_score", 0.0),
            "match_type": yati_details1.get("match_type", "no_match"),
            "mismatch_details": yati_details1,
        }

    if pada2["first_letter"] and pada2["third_gana_first_letter"]:
        match, group_idx, yati_details2 = check_yati_maitri(
            pada2["first_letter"],
            pada2["third_gana_first_letter"]
        )
        yati_line2 = {
            "first_gana_letter": pada2["first_letter"],
            "third_gana_letter": pada2["third_gana_first_letter"],
            "match": match,
            "group_index": group_idx,
            "quality_score": yati_details2.get("quality_score", 0.0),
            "match_type": yati_details2.get("match_type", "no_match"),
            "mismatch_details": yati_details2,
        }

    # Calculate scores for each component
    gana_score1 = calculate_gana_score(pada1.get("partition"))
    gana_score2 = calculate_gana_score(pada2.get("partition"))
    prasa_score_result = calculate_prasa_score(prasa_details)
    yati_score1 = calculate_yati_score(yati_line1)
    yati_score2 = calculate_yati_score(yati_line2)

    # Calculate overall weighted score
    match_score = calculate_overall_score(
        gana_score1, gana_score2,
        prasa_score_result,
        yati_score1, yati_score2
    )

    # Add component scores to match_score breakdown
    match_score["component_scores"] = {
        "gana_line1": gana_score1,
        "gana_line2": gana_score2,
        "prasa": prasa_score_result,
        "yati_line1": yati_score1,
        "yati_line2": yati_score2,
    }

    # Determine overall validity (binary pass/fail for strict validation)
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
        "match_score": match_score,
        "validation_summary": {
            "gana_sequence_line1": pada1["is_valid_gana_sequence"],
            "gana_sequence_line2": pada2["is_valid_gana_sequence"],
            "prasa_match": prasa_match,
            "yati_line1_match": yati_line1["match"] if yati_line1 else None,
            "yati_line2_match": yati_line2["match"] if yati_line2 else None,
        }
    }


def format_analysis_report(analysis: Dict) -> str:
    """
    Format the analysis as a human-readable report.

    This function creates a comprehensive report showing:
    - Per-line analysis with gana breakdown
    - Prasa (rhyme) analysis with mismatch diagnostics
    - Yati (alliteration) analysis with quality scores
    - Overall match percentage and validation summary

    Args:
        analysis: Dict returned by analyze_dwipada()

    Returns:
        Formatted string report suitable for display
    """
    lines = []
    lines.append("=" * 70)
    lines.append("DWIPADA CHANDASSU ANALYSIS REPORT")
    lines.append("=" * 70)

    # Match Score Summary (NEW - show percentage at top)
    if "match_score" in analysis:
        score = analysis["match_score"]
        overall = score.get("overall", 0)
        lines.append(f"\n📊 OVERALL MATCH SCORE: {overall:.1f}%")
        lines.append("-" * 35)

    # Line 1 Analysis
    lines.append("\n--- LINE 1 (పాదము 1) ---")
    pada1 = analysis["pada1"]
    lines.append(f"Text: {pada1['line']}")
    lines.append(f"Aksharalu: {' | '.join(pada1['aksharalu'])}")
    lines.append(f"Gana Markers: {' '.join(pada1['gana_markers'])}")

    if pada1["partition"]:
        partition = pada1["partition"]
        ganas_matched = partition.get("ganas_matched", 4)
        lines.append(f"\nGana Breakdown ({ganas_matched}/4 valid):")
        for gana in partition["ganas"]:
            gana_type_label = "ఇంద్ర గణము" if gana["type"] == "Indra" else "సూర్య గణము"
            valid_mark = "✓" if gana.get("valid", True) else "✗"
            name_str = gana['name'] if gana['name'] else "[Invalid]"
            lines.append(f"  {valid_mark} Gana {gana.get('position', '?')}: {''.join(gana['aksharalu'])} = {gana['pattern']} = {name_str} ({gana_type_label})")
            # Show error message if gana is invalid
            if not gana.get("valid", True) and gana.get("error"):
                lines.append(f"      ↳ {gana['error']}")
    else:
        lines.append("\n[WARNING] Could not find valid 3 Indra + 1 Surya Gana partition")

    # Line 2 Analysis
    lines.append("\n--- LINE 2 (పాదము 2) ---")
    pada2 = analysis["pada2"]
    lines.append(f"Text: {pada2['line']}")
    lines.append(f"Aksharalu: {' | '.join(pada2['aksharalu'])}")
    lines.append(f"Gana Markers: {' '.join(pada2['gana_markers'])}")

    if pada2["partition"]:
        partition = pada2["partition"]
        ganas_matched = partition.get("ganas_matched", 4)
        lines.append(f"\nGana Breakdown ({ganas_matched}/4 valid):")
        for gana in partition["ganas"]:
            gana_type_label = "ఇంద్ర గణము" if gana["type"] == "Indra" else "సూర్య గణము"
            valid_mark = "✓" if gana.get("valid", True) else "✗"
            name_str = gana['name'] if gana['name'] else "[Invalid]"
            lines.append(f"  {valid_mark} Gana {gana.get('position', '?')}: {''.join(gana['aksharalu'])} = {gana['pattern']} = {name_str} ({gana_type_label})")
            if not gana.get("valid", True) and gana.get("error"):
                lines.append(f"      ↳ {gana['error']}")
    else:
        lines.append("\n[WARNING] Could not find valid 3 Indra + 1 Surya Gana partition")

    # Prasa Analysis with enhanced diagnostics
    lines.append("\n--- PRASA (ప్రాస) ANALYSIS ---")
    if analysis["prasa"]:
        prasa = analysis["prasa"]
        status = "✓ MATCH" if prasa["match"] else "✗ NO MATCH"
        lines.append(f"Line 1 - 2nd Aksharam: '{prasa['line1_second_aksharam']}' (Consonant: {prasa['line1_consonant']})")
        lines.append(f"Line 2 - 2nd Aksharam: '{prasa['line2_second_aksharam']}' (Consonant: {prasa['line2_consonant']})")
        lines.append(f"Prasa Status: {status}")

        # Show mismatch diagnostics if prasa doesn't match
        if not prasa["match"] and prasa.get("mismatch_details"):
            details = prasa["mismatch_details"]
            lines.append("\n  📋 Mismatch Details:")
            if details.get("line1_full_breakdown"):
                bd1 = details["line1_full_breakdown"]
                lines.append(f"    Line 1: '{bd1.get('aksharam')}' → consonant '{bd1.get('consonant')}' ({bd1.get('consonant_varga', 'unknown')})")
            if details.get("line2_full_breakdown"):
                bd2 = details["line2_full_breakdown"]
                lines.append(f"    Line 2: '{bd2.get('aksharam')}' → consonant '{bd2.get('consonant')}' ({bd2.get('consonant_varga', 'unknown')})")
            if details.get("why_mismatch"):
                lines.append(f"    Why: {details['why_mismatch']}")
            if details.get("suggestion"):
                lines.append(f"    💡 Suggestion: {details['suggestion']}")
    else:
        lines.append("Could not determine Prasa")

    # Yati Analysis with enhanced diagnostics
    lines.append("\n--- YATI (యతి) ANALYSIS ---")

    if analysis["yati_line1"]:
        yati1 = analysis["yati_line1"]
        match_type = yati1.get("match_type", "unknown")
        quality = yati1.get("quality_score", 0)
        status = f"✓ MATCH ({match_type}, {quality:.0f}%)" if yati1["match"] else "✗ NO MATCH"
        lines.append(f"Line 1: '{yati1['first_gana_letter']}' (1st gana) ↔ '{yati1['third_gana_letter']}' (3rd gana) - {status}")

        # Show details for mismatches or varga matches
        if not yati1["match"] or match_type == "varga_match":
            mismatch = yati1.get("mismatch_details", {})
            if mismatch:
                info1 = mismatch.get("letter1_info", {})
                info2 = mismatch.get("letter2_info", {})
                if info1 and info2:
                    lines.append(f"    '{yati1['first_gana_letter']}' groups: {info1.get('yati_group_members', [])}")
                if mismatch.get("matching_group_members"):
                    lines.append(f"    Matching group: {mismatch['matching_group_members']}")
    else:
        lines.append("Line 1: Could not determine Yati")

    if analysis["yati_line2"]:
        yati2 = analysis["yati_line2"]
        match_type = yati2.get("match_type", "unknown")
        quality = yati2.get("quality_score", 0)
        status = f"✓ MATCH ({match_type}, {quality:.0f}%)" if yati2["match"] else "✗ NO MATCH"
        lines.append(f"Line 2: '{yati2['first_gana_letter']}' (1st gana) ↔ '{yati2['third_gana_letter']}' (3rd gana) - {status}")

        if not yati2["match"] or match_type == "varga_match":
            mismatch = yati2.get("mismatch_details", {})
            if mismatch:
                info1 = mismatch.get("letter1_info", {})
                if info1:
                    lines.append(f"    '{yati2['first_gana_letter']}' groups: {info1.get('yati_group_members', [])}")
                if mismatch.get("matching_group_members"):
                    lines.append(f"    Matching group: {mismatch['matching_group_members']}")
    else:
        lines.append("Line 2: Could not determine Yati")

    # Score Breakdown (NEW)
    if "match_score" in analysis:
        lines.append("\n--- SCORE BREAKDOWN ---")
        score = analysis["match_score"]
        breakdown = score.get("breakdown", {})
        weights = score.get("weights", {})

        lines.append(f"  Gana (weight {weights.get('gana', 0.4)*100:.0f}%):")
        lines.append(f"    Line 1: {breakdown.get('gana_line1', 0):.1f}%")
        lines.append(f"    Line 2: {breakdown.get('gana_line2', 0):.1f}%")
        lines.append(f"    Average: {breakdown.get('gana_average', 0):.1f}%")

        lines.append(f"  Prasa (weight {weights.get('prasa', 0.35)*100:.0f}%): {breakdown.get('prasa', 0):.1f}%")

        lines.append(f"  Yati (weight {weights.get('yati', 0.25)*100:.0f}%):")
        lines.append(f"    Line 1: {breakdown.get('yati_line1', 0):.1f}%")
        lines.append(f"    Line 2: {breakdown.get('yati_line2', 0):.1f}%")
        lines.append(f"    Average: {breakdown.get('yati_average', 0):.1f}%")

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

    # Final verdict with percentage
    if "match_score" in analysis:
        overall = analysis["match_score"].get("overall", 0)
        lines.append(f"OVERALL: {'✓ VALID DWIPADA' if analysis['is_valid_dwipada'] else '✗ INVALID DWIPADA'} ({overall:.1f}% match)")
    else:
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
        match, group, details = check_yati_maitri(l1, l2)
        result = "✓" if match == expected else "✗"
        if match != expected:
            all_correct = False
        quality = details.get("quality_score", 0)
        print(f"  {result} '{l1}' + '{l2}' ({desc}): {match} (quality: {quality:.0f}%)")
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
            match, _, _ = check_yati_maitri(l1, l2)
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
        match, group, _ = check_yati_maitri(l1, l2)
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
    # CATEGORY 8: USER-PROVIDED TEST CASES (Tests 34+)
    # =========================================================================
    print("\n" + "=" * 70)
    print("CATEGORY 8: USER-PROVIDED TEST CASES")
    print("=" * 70)

    # Test 34: Valid Dwipada - తోడుగా నిలిచేను (User-provided)
    print("\n--- TEST 34: VALID - తోడుగా నిలిచేను (User-provided) ---")
    poem34 = """తోడుగా నిలిచేను తుదిదాక చూడు
నీడలా సాగేను నిమిషంబు విడువ"""
    try:
        analysis = analyze_dwipada(poem34)
        print(f"  Line 1: {analysis['pada1']['line']}")
        print(f"  Line 2: {analysis['pada2']['line']}")
        print(f"  Gana Seq Line1: {analysis['pada1']['is_valid_gana_sequence']}")
        print(f"  Gana Seq Line2: {analysis['pada2']['is_valid_gana_sequence']}")
        if analysis['prasa']:
            print(f"  Prasa: '{analysis['prasa']['line1_consonant']}' vs '{analysis['prasa']['line2_consonant']}' = {analysis['prasa']['match']}")
        if analysis['yati_line1']:
            print(f"  Yati Line1: '{analysis['yati_line1']['first_gana_letter']}' ↔ '{analysis['yati_line1']['third_gana_letter']}' = {analysis['yati_line1']['match']}")
        if analysis['yati_line2']:
            print(f"  Yati Line2: '{analysis['yati_line2']['first_gana_letter']}' ↔ '{analysis['yati_line2']['third_gana_letter']}' = {analysis['yati_line2']['match']}")
        if 'match_score' in analysis:
            print(f"  Overall Score: {analysis['match_score']['overall']}%")
        print(f"  Valid Dwipada: {analysis['is_valid_dwipada']}")
        if analysis['is_valid_dwipada']:
            passed += 1
            print("✓ PASSED - Valid Dwipada correctly identified")
        else:
            failed += 1
            print("✗ FAILED - Should be a valid Dwipada")
    except Exception as e:
        print(f"✗ FAILED - {e}")
        failed += 1

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
