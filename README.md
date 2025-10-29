# AuctionDimensionProcessor
Automated dimension extraction and classification system for auction lot descriptions-Python script that processes auction catalog data to automatically extract, standardize, and classify item dimensions for shipping calculations. Designed to handle the highly variable and unpredictable nature of auction lot descriptions in French and English.


**Automated dimension extraction and classification system for auction lot descriptions**

## Overview

Python script that processes auction catalog data to automatically extract, standardize, and classify item dimensions for shipping calculations. Designed to handle the highly variable and unpredictable nature of auction lot descriptions in French and English.

## Key Features

### Intelligent Dimension Extraction
- **Multiple format support**: Handles labeled (H×L×P), unlabeled (50×40×30 cm), 2D, diameter (Ø), and scattered individual dimensions
- **Smart pattern matching**: Prioritizes complete patterns, falls back to individual label extraction when needed
- **Multi-dimension handling**: Detects and manages items with multiple dimension sets (e.g., "45×34cm (canvas) 80×34cm (with frame)")

### Automatic 2D/3D Classification
- **Material-based recognition**: Identifies 2D artworks (paintings, prints, photos, textiles) vs 3D objects (sculptures, furniture, assemblages)
- **Context-aware logic**: Distinguishes between paintings on panels vs sculptural reliefs, traditional works vs mixed-media assemblages
- **Default depth assignment**: Assigns D=5cm for 2D items, applies intelligent fallback rules for incomplete 3D dimensions

### Smart Edge Case Detection
Automatically flags ambiguous cases for manual review:
- Fashion items with sizing notation (S/M/L)
- Books with volume numbers misinterpreted as dimensions
- Items using non-standard "D" depth notation
- Rugs with ambiguous shipping requirements (flat vs rolled)
- Curtains with unclear pair/panel counts
- Height-only objects missing width/depth
- Assemblages with unpredictable depth
- Single items with multiple conflicting dimension sets

### Item Count Intelligence
- **Natural language parsing**: Detects item counts from French/English number words ("trois", "paire de", "ensemble de")
- **Context exclusion**: Ignores edition numbering ("édition de trois exemplaires")
- **Ambiguity detection**: Flags lots with "chaque" (each) for count verification

## Processing Output

**One row per lot** with:
- Standardized H, L, D dimensions (H_1, L_1, D_1 columns up to max item count)
- Item classification (2D/3D/MANUAL_CHECK)
- Item count detection
- Material extraction
- Processing flags and conversion logs for transparency
- `MANUAL_REVIEW_REQUIRED` boolean for easy filtering

## Technical Approach

### Design Philosophy
**Conservative automation**: Prioritizes accuracy over aggressive processing. When uncertain, flags for human review rather than risk incorrect automated decisions (~16% manual review rate).

### Key Logic
- **Material-first classification** with dimension pattern validation
- **Hierarchical pattern matching** from most specific to fallback extraction
- **Defensive coding** with preemptive logic for edge cases
- **Transparent processing** with detailed flags and conversion logs

## Known Limitations

Accepts certain edge cases as manual review items rather than risk false positives:
- **Context-based false positives**: Numbers in gallery names, bibliography references (e.g., "Galerie des Quatre Chemins" → 4 items)
- **Mixed item types**: Cannot semantically distinguish "table et quatre chaises" (5 items: 1 table + 4 chairs)
- **Source data quality**: Unusual spacing or typos in dimension notation

## Statistics (Example Dataset: 791 lots)

- **84% automated**: 665 lots processed automatically with complete dimensions
- **16% flagged**: 126 lots requiring manual review for ambiguous/incomplete data
- **Classification**: 58% 3D objects, 37% 2D artworks, 5% indeterminate

## Tech Stack

- Python 3.x
- Pandas for data processing
- Regex for pattern matching
- Openpyxl for Excel I/O

## Use Case

Designed for auction houses and art logistics companies needing to:
- Process hundreds/thousands of lot descriptions rapidly
- Standardize inconsistent dimension notation
- Calculate shipping dimensions for diverse item types
- Flag edge cases requiring expert verification

---

**Built to handle the chaos of real-world auction catalogs with intelligence, transparency, and pragmatism.**
