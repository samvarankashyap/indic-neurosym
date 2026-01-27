# Indic-NeuroSym

**A Neuro-Symbolic Logits Processor for Strict Metrical Generation in Low-Resource SLMs**

This repository contains foundational tools and datasets for enabling strict metrical poetry generation in Telugu using neuro-symbolic approaches with Small Language Models (SLMs).

---

## Overview

Generating metrically correct poetry in low-resource Indic languages is challenging due to:
- Complex prosodic rules (Chandassu) governing syllable patterns
- Lack of annotated datasets for training
- Limited tokenizer support for Indic scripts in mainstream LLMs

**Indic-NeuroSym** addresses these challenges by providing:

1. **Rule-based prosody analyzers** that can validate and constrain LLM outputs
2. **Web crawlers** for building Telugu poetry corpora from public sources
3. **Symbolic constraint systems** for Dwipada meter validation (Gana, Yati, Prasa rules)

---

## Project Structure

```
inlp_project/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── config.yaml                        # API keys (not tracked in git)
│
├── dwipada_analyzer.py                # Core: Telugu Dwipada prosody analyzer
├── aksharanusarika.py                 # Telugu linguistic analysis library
├── gemini_client.py                   # Gemini API client for poetry generation
│
├── crawl_dwipada_bhagavatam.py        # Crawler: Dwipada Bhagavatam from Wikisource
├── crawl_ranganatha_ramayanam.py      # Crawler: Ranganatha Ramayanam from AndhaBharati
├── crawl_srirama_parinayamu.py        # Crawler: Sri Rama Parinayamu from Wikisource
├── crawl_basava_puranam.py            # Crawler: Basava Puranam from Wikisource
├── clean_srirama_parinayamu.py        # Cleaner: Remove punctuation from Sri Rama Parinayamu
├── clean_basava_puranam.py            # Cleaner: Remove punctuation from Basava Puranam
│
└── data/                              # 687 files, 60,334 couplets total
    ├── ranganatha_ramayanam/          # 405 files, 53,457 couplets
    │   ├── 01_BalaKanda/
    │   ├── 02_AyodhyaKanda/
    │   ├── 03_AranyaKanda/
    │   ├── 04_KishkindhaKanda/
    │   ├── 05_SundaraKanda/
    │   ├── 06_YuddhaKanda/
    │   └── 07_UttaraKanda/
    │
    ├── dwipada_bhagavatam/            # 207 files, 3,624 couplets
    │   ├── 01_MadhuraKanda/
    │   ├── 02_KalyanaKanda/
    │   └── 03_JagadabhirakshaKanda/
    │
    ├── basava_puranam/                # 47 files, 2,455 couplets
    │   ├── 001_ప్రథమాశ్వాసము/
    │   ├── 002_ద్వితీయాశ్వాసము/
    │   └── 003_తృతీయాశ్వాసము/
    │
    └── srirama_parinayamu/            # 28 files, 798 couplets
```

---

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd inlp_project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration (Optional - for Gemini API)

Create a `config.yaml` file with your Gemini API key:

```yaml
api_key: "your-gemini-api-key-here"
```

---

## Usage

### 1. Dwipada Analyzer (`dwipada_analyzer.py`)

The core prosody analysis tool for Telugu Dwipada meter validation.

#### Run Tests
```bash
python dwipada_analyzer.py
```

This runs the comprehensive test suite (33 tests) covering:
- Aksharam (syllable) splitting
- Gana (prosodic unit) identification
- Yati (caesura) detection
- Prasa (rhyme) validation

#### Use as a Module

```python
from dwipada_analyzer import (
    analyze_dwipada,
    analyze_pada,
    split_aksharalu,
    check_prasa,
    check_yati_maitri
)

# Analyze a complete Dwipada couplet
poem = """సౌధాగ్రముల యందు సదనంబు లందు
వీధుల యందును వెఱవొప్ప నిలిచి"""

result = analyze_dwipada(poem)

print(f"Valid Dwipada: {result['is_valid_dwipada']}")
print(f"Prasa Match: {result['prasa']['match']}")
print(f"Yati Match Line 1: {result['yati_line1']['match']}")
```

#### Key Functions

| Function | Description |
|----------|-------------|
| `split_aksharalu(text)` | Split Telugu text into syllables (aksharalu) |
| `akshara_ganavibhajana(aksharalu)` | Mark syllables as Guru (U) or Laghu (I) |
| `analyze_pada(line)` | Analyze a single line for gana sequence |
| `analyze_dwipada(poem)` | Full analysis of 2-line Dwipada |
| `check_prasa(line1, line2)` | Check rhyme between two lines |
| `check_yati_maitri(letter1, letter2)` | Check if letters belong to same Yati group |

---

### 2. Aksharanusarika (`aksharanusarika.py`)

Advanced Telugu linguistic analysis library with comprehensive prosody features.

```python
from aksharanusarika import (
    split_aksharalu,
    categorize_aksharam,
    akshara_ganavibhajana,
    jaccard_similarity_linguistic_features
)

# Split word into syllables
word = "కృష్ణుడు"
syllables = split_aksharalu(word)
print(syllables)  # ['కృ', 'ష్ణు', 'డు']

# Get linguistic categories for a syllable
categories = categorize_aksharam("కృ")
print(categories)  # {'హల్లు', 'ఋకారం', ...}
```

---

### 3. Data Crawlers

#### Crawl Ranganatha Ramayanam
```bash
python crawl_ranganatha_ramayanam.py
```
- **Source**: `andhrabharati.com/itihAsamulu/RanganathaRamayanamu/`
- **Output**: `data/ranganatha_ramayanam/` (405 chapters, 7 kandas)

#### Crawl Dwipada Bhagavatam
```bash
python crawl_dwipada_bhagavatam.py
```
- **Source**: `te.wikisource.org/wiki/ద్విపదభాగవతము/`
- **Output**: `data/dwipada_bhagavatam/` (207 chapters, 3 kandas)

#### Crawl Basava Puranam
```bash
python crawl_basava_puranam.py
python clean_basava_puranam.py  # Optional: remove punctuation
```
- **Source**: `te.wikisource.org/wiki/బసవపురాణము/`
- **Output**: `data/basava_puranam/` (47 sections, 3 ఆశ్వాసములు)

#### Crawl Sri Rama Parinayamu
```bash
python crawl_srirama_parinayamu.py
python clean_srirama_parinayamu.py  # Optional: remove punctuation
```
- **Source**: `te.wikisource.org/wiki/శ్రీరమాపరిణయము/`
- **Output**: `data/srirama_parinayamu/` (28 chapters)

---

### 4. Gemini Client (`gemini_client.py`)

Generate Dwipada poetry using Google's Gemini API.

```bash
# Ensure config.yaml has your API key
python gemini_client.py
```

The client:
- Uses a detailed prompt with Dwipada construction rules
- Logs responses to `gemini_responses.txt`
- Can be customized by editing the `PROMPT` variable

---

## Dwipada Meter Rules

### Structure
Each Dwipada consists of 2 lines (padas), with each line containing:
- **3 Indra Ganas** + **1 Surya Gana** (total 4 ganas per line)

### Gana Types

#### Indra Ganas (3-4 syllables)
| Pattern | Name | Telugu |
|---------|------|--------|
| IIII | Nala | నల |
| IIIU | Naga | నగ |
| IIUI | Sala | సల |
| UII | Bha | భ |
| UIU | Ra | ర |
| UUI | Ta | త |

#### Surya Ganas (2-3 syllables)
| Pattern | Name | Telugu |
|---------|------|--------|
| III | Na | న |
| UI | Ha/Gala | హ/గల |

### Guru (U) / Laghu (I) Rules
- **Laghu (I)**: Short vowels (అ, ఇ, ఉ, ఋ, ఎ, ఒ)
- **Guru (U)**:
  - Long vowels (ఆ, ఈ, ఊ, ఏ, ఓ, ఔ)
  - Syllables with Anuswara (ం) or Visarga (ః)
  - Syllable before a conjunct consonant (సంయుక్తాక్షరం)

### Yati (యతి) - Caesura
The first letter of the 3rd Gana must match (by Yati Maitri rules) with the first letter of the 1st Gana.

### Prasa (ప్రాస) - Rhyme
The base consonant of the 2nd syllable in Line 1 must match the base consonant of the 2nd syllable in Line 2.

---

## Datasets

### Telugu Poetry Corpus Summary

| Dataset | Source | Files | Couplets |
|---------|--------|------:|--------:|
| **రంగనాథ రామాయణము** | AndhaBharati.com | 405 | 53,457 |
| **ద్విపద భాగవతము** | te.wikisource.org | 207 | 3,624 |
| **బసవపురాణము** | te.wikisource.org | 47 | 2,455 |
| **శ్రీరమాపరిణయము** | te.wikisource.org | 28 | 798 |
| **TOTAL** | | **687** | **60,334** |

---

### రంగనాథ రామాయణము (Ranganatha Ramayanam)
- **Source**: AndhaBharati.com
- **Author**: గోన బుద్ధారెడ్డి (Gona Budda Reddy)
- **Format**: Dwipada (ద్విపద) meter

| Kanda | Files | Couplets |
|-------|------:|--------:|
| బాలకాండము | 31 | 5,407 |
| అయోధ్యాకాండము | 35 | 4,396 |
| అరణ్యకాండము | 28 | 3,368 |
| కిష్కింధాకాండము | 25 | 3,021 |
| సుందరకాండము | 27 | 3,794 |
| యుద్ధకాండము | 170 | 22,785 |
| ఉత్తరకాండము | 89 | 10,686 |

### ద్విపద భాగవతము (Dwipada Bhagavatam)
- **Source**: Telugu Wikisource
- **Format**: Dwipada (ద్విపద) meter

| Kanda | Files | Couplets |
|-------|------:|--------:|
| మధురకాండ | 77 | 2,223 |
| కల్యాణకాండ | 88 | 934 |
| జగదభిరక్షకాండ | 42 | 467 |

### బసవపురాణము (Basava Puranam)
- **Source**: Telugu Wikisource
- **Author**: పాల్కురికి సోమనాథుడు (Palkuriki Somanatha)
- **Format**: Dwipada (ద్విపద) meter

| Ashvasam | Files | Couplets |
|----------|------:|--------:|
| ప్రథమాశ్వాసము | 11 | 634 |
| ద్వితీయాశ్వాసము | 22 | 663 |
| తృతీయాశ్వాసము | 14 | 1,158 |

### శ్రీరమాపరిణయము (Sri Rama Parinayamu)
- **Source**: Telugu Wikisource
- **Author**: తరిగొండ వెంగమాంబ (Tarigonda Vengamamba)
- **Chapters**: 28
- **Couplets**: 798
- **Format**: Dwipada (ద్విపద) meter

---

### File Format
```
# గ్రంథము: బసవపురాణము
# ఆశ్వాసము: ప్రథమాశ్వాసము
# విభాగము: 001
# శీర్షిక: శ్రీరస్తు

[Telugu verse content]
```

For Ranganatha Ramayanam (includes footnotes):
```
# కాండము: బాలకాండము
# అధ్యాయము: 001
# శీర్షిక: Chapter Title

[Telugu verse content]

---
పాదసూచికలు (Footnotes):
[1] Footnote text
```

---

## Research Context

This project supports research in:

1. **Constrained Text Generation**: Using symbolic rules to guide neural language models
2. **Low-Resource NLP**: Building tools for Telugu and other Indic languages
3. **Neuro-Symbolic AI**: Combining neural generation with logical constraints
4. **Computational Poetics**: Automated analysis and generation of metrical poetry

### Potential Applications

- **Logits Processor**: Use `dwipada_analyzer.py` as a constraint validator during LLM decoding
- **Training Data**: Use crawled corpora for fine-tuning poetry generation models
- **Evaluation Metrics**: Validate generated poetry against strict metrical rules

---

## Running Tests

```bash
# Run Dwipada Analyzer test suite
python dwipada_analyzer.py

# Expected output:
# ======================================================================
# DWIPADA ANALYZER - COMPREHENSIVE TEST SUITE
# ======================================================================
# ...
# TEST SUMMARY
# ======================================================================
#   Total Tests: 33
#   Passed: 33
#   Failed: 0
#   Success Rate: 100.0%
# ======================================================================
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `google-genai` | Gemini API client |
| `PyYAML` | Configuration file parsing |
| `requests` | HTTP requests for crawlers |
| `beautifulsoup4` | HTML parsing |
| `lxml` | Fast XML/HTML parser |

---

## License

[Specify your license here]

---

## Citation

If you use this work in your research, please cite:

```bibtex
@software{indic_neurosym,
  title = {Indic-NeuroSym: A Neuro-Symbolic Logits Processor for Strict Metrical Generation in Low-Resource SLMs},
  author = {[Your Name]},
  year = {2025},
  url = {[repository-url]}
}
```

---

## Acknowledgments

- **Telugu Wikisource** (te.wikisource.org) for:
  - ద్విపద భాగవతము (Dwipada Bhagavatam)
  - బసవపురాణము (Basava Puranam) by పాల్కురికి సోమనాథుడు
  - శ్రీరమాపరిణయము (Sri Rama Parinayamu) by తరిగొండ వెంగమాంబ
- **AndhaBharati.com** for రంగనాథ రామాయణము (Ranganatha Ramayanam)
- Traditional Telugu prosody scholars for Chandassu documentation
