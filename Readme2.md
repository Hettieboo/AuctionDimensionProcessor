# Auction Dimension Processor - Documentation

## Table of Contents
1. [Overview](#overview)
2. [Setup & Installation](#setup--installation)
3. [Input Requirements](#input-requirements)
4. [How to Run](#how-to-run)
5. [Output Schema](#output-schema)
6. [Processing Flags Reference](#processing-flags-reference)
7. [Usage Guide](#usage-guide)
8. [Known Limitations](#known-limitations)
9. [Troubleshooting](#troubleshooting)
10. [Configuration](#configuration)

---

## Overview

Automated system for processing auction lot descriptions to extract, standardize, and classify item dimensions for shipping calculations. Handles French and English descriptions with intelligent 2D/3D classification.

**Key capabilities:**
- Extracts dimensions from various formats (H×L×P, H×Ø, unlabeled, etc.)
- Classifies items as 2D (flat artworks) or 3D (physical objects)
- Detects item counts from natural language
- Flags ambiguous cases for manual review
- Provides transparent processing logs

---

## Setup & Installation

### Requirements
- Python 3.x
- Excel file with auction data

### Installation
```bash
pip install pandas openpyxl
```

### File Structure
```
project/
├── auction_processor.py          # Main script
├── your_input_file.xlsx          # Input data
└── auction_dimensions_output.xlsx # Generated output
```

---

## Input Requirements

### Required Columns
Your Excel file **MUST** contain these columns (exact spelling):

| Column Name | Type | Description | Example |
|------------|------|-------------|---------|
| `LOT` | Text/Number | Unique lot identifier | "230235" or "2302 35" |
| `TYPESET` | Text | Full lot description in French/English | "Huile sur toile, 50×40 cm" |

### Optional Columns
Any other columns in your file will be preserved in the output (estimates, provenance, etc.)

### Data Requirements
- **File format**: `.xlsx` (Excel)
- **Language**: French and/or English descriptions
- **Encoding**: UTF-8 compatible
- **No empty TYPESET cells**: Each lot must have a description

### Input File Configuration
**Important:** Update the filename in the script (line ~593):
```python
df = pd.read_excel('YOUR_FILENAME_HERE.xlsx')
```

---

## How to Run

### Basic Execution
1. Place your Excel file in the same directory as the script
2. Update the filename in the script (see above)
3. Run:
```bash
python auction_processor.py
```

### Expected Console Output
```
Starting One-Row-Per-LOT Processing...
Loaded 791 rows
Processing 791 lots...
Progress: 0/791
Progress: 100/791
...

Completed! 791 lots processed
Manual review required: 126

Processing Summary:
Item Type Distribution:
  3D: 459
  2D: 290
  MANUAL_CHECK: 42

Maximum items in a single lot: 36
Lot with most items: LOT 208.0 (36 items)

Manual Review Reasons (top 5):
  : 70
  MULTIPLE_DIMENSIONS_SINGLE_ITEM: 14
  CHAQUE_DETECTED: 12
  ...

Done! File saved as 'auction_dimensions_one_row_per_lot.xlsx'
```

### Processing Time
- ~100 lots/second
- 1,000 lots ≈ 10 seconds

---

## Output Schema

### Output File
**Filename**: `auction_dimensions_one_row_per_lot.xlsx`

### New Columns Added

#### Core Classification
| Column | Type | Values | Description |
|--------|------|--------|-------------|
| `ITEM_COUNT` | Integer | 1-n | Number of items in lot |
| `ITEM_TYPE` | String | 2D / 3D / MANUAL_CHECK | Physical classification |
| `MATERIAL` | String | "Canvas, Wood" | Extracted materials (English) |
| `MANUAL_REVIEW_REQUIRED` | Boolean | TRUE / FALSE | Needs human verification |

#### Dimensions (per item)
Columns created for each item up to maximum count in dataset:

| Column Pattern | Type | Description |
|---------------|------|-------------|
| `H_1`, `H_2`, ... | Float | Height in cm |
| `L_1`, `L_2`, ... | Float | Length in cm |
| `D_1`, `D_2`, ... | Float | Depth in cm |
| `P_1`, `P_2`, ... | Float | Original P value (if extracted) |
| `Diameter_1`, `Diameter_2`, ... | Float | Diameter (Ø) if applicable |

#### Processing Metadata
| Column | Type | Description |
|--------|------|-------------|
| `PROCESSING_FLAGS` | String | Semicolon-separated flags (see reference below) |
| `CONVERSION_LOG` | String | Step-by-step processing notes |

### Example Output Row

| LOT | TYPESET | ITEM_COUNT | ITEM_TYPE | H_1 | L_1 | D_1 | MANUAL_REVIEW_REQUIRED | PROCESSING_FLAGS | CONVERSION_LOG |
|-----|---------|------------|-----------|-----|-----|-----|----------------------|------------------|----------------|
| 235 | Huile sur toile 45×34cm | 1 | 2D | 34 | 45 | 5 | FALSE | | Item 1: L=max(H,L); Item 1: D=5 (2D) |

---

## Processing Flags Reference

### Flags Requiring Manual Review

| Flag | Meaning | Action Required |
|------|---------|-----------------|
| `MULTIPLE_DIMENSIONS_SINGLE_ITEM` | One item with conflicting dimension sets (e.g., "45×34cm (canvas) 80×34cm (framed)") | Verify which dimensions to use |
| `CHAQUE_DETECTED` | Contains "chaque" (each) - item count may be ambiguous | Verify actual item count |
| `FASHION_ITEM` | Contains "Taille" (Size S/M/L) - garment sizing ≠ shipping dimensions | Measure actual dimensions |
| `ASSEMBLAGE_3D_MANUAL_CHECK` | Physical assemblage with objects - D=5 is placeholder | Verify actual depth |
| `D_NOTATION_DEPTH` | Uses "D" notation for depth (extraction failed) | Enter dimensions manually |
| `RUG_L_P_PATTERN` | Rug with L×P dimensions - shipping method unclear | Specify flat or rolled |
| `CURTAIN_PAIR_COUNT` | Curtains with "paire" - count ambiguous (pairs vs panels) | Count actual panels |
| `BOOK_DIMENSION_CHECK` | Book with extracted dimensions (likely volume numbers) | Ignore fake dimensions, measure books |
| `HEIGHT_ONLY_OBJECT` | Only height extracted (e.g., cane H: 97cm) | Add missing L and D |
| `HIGH_COUNT` | More than 10 items - dimension replication may be incorrect | Verify dimensions for each item |
| `NO_DIMENSIONS` | No measurements found in description | Enter all dimensions manually |
| `OUVERT/FERMÉ` | Marked "Open" or "Closed" - no processing attempted | Handle separately |

### Informational Flags (No Action Required)

| Flag | Meaning |
|------|---------|
| `PANEL_OBJECT_3D` | Panel object assigned D=5 (informational) |
| `TECHNIQUE_MIXTE_TOILE_RECLASSIFIED` | Reclassified from 3D to 2D based on material |
| `DECADRER_2D` | Identified as framed work via "à décadrer" |

---

## Usage Guide

### Filtering for Manual Review

**Excel:**
1. Apply AutoFilter to header row
2. Filter `MANUAL_REVIEW_REQUIRED` column → Show only `TRUE`

**Python/Pandas:**
```python
manual_review = df[df['MANUAL_REVIEW_REQUIRED'] == True]
```

### Understanding CONVERSION_LOG

Common log entries:

| Log Entry | Meaning |
|-----------|---------|
| `Item 1: L=max(H,L); Item 1: D=5 (2D)` | 2D item - swapped H/L to make L longer, assigned depth=5cm |
| `Item 1: D=P` | 3D item - depth taken from P dimension |
| `Item 1: D=L` | 3D item with H×L only - assumed depth = length |
| `Item 1: L=Ø, D=Ø` | Cylindrical item - length and depth from diameter |
| `Replicated dimensions to match X items` | Fewer dimension sets than items - dimensions copied |
| `Single item with multiple dimension sets - using largest dimensions only` | Multiple sizes found - kept largest |

### Common Scenarios

#### Scenario 1: Standard 2D Artwork
**Input:** "Huile sur toile 162 x 130 cm"
- `ITEM_TYPE`: 2D
- `H_1`: 130, `L_1`: 162, `D_1`: 5
- `MANUAL_REVIEW_REQUIRED`: FALSE

#### Scenario 2: 3D Sculpture
**Input:** "Bronze H 50 × L 40 × P 30 cm"
- `ITEM_TYPE`: 3D
- `H_1`: 50, `L_1`: 40, `D_1`: 30
- `MANUAL_REVIEW_REQUIRED`: FALSE

#### Scenario 3: Ambiguous Case
**Input:** "Paire de vases, chaque 30cm"
- `ITEM_TYPE`: 3D
- `ITEM_COUNT`: 2
- `MANUAL_REVIEW_REQUIRED`: TRUE
- `PROCESSING_FLAGS`: "CHAQUE_DETECTED: manual count verification needed"

---

## Known Limitations

### Accepted Limitations (Manual Review Required)

#### 1. Context-Based False Positives
**Issue:** Numbers in provenance/bibliography detected as item counts

**Examples:**
- "deux collections de psychiatres" → detects 2 items (should be 1)
- "Galerie des Quatre Chemins" → detects 4 items (should be 1)
- "Quatre-vingts ans de surréalisme" (book title) → detects 4 items (should be 1)

**Why accepted:** Would require complex text parsing to isolate sections; risks missing legitimate counts in similar contexts

**User action:** Manually correct item count in output

---

#### 2. Mixed Item Types
**Issue:** Cannot distinguish different furniture types

**Example:**
- "Table et quatre chaises" → detects 4 items (should be 5: 1 table + 4 chairs)
- Alternates chair/table dimensions incorrectly

**Why accepted:** Requires semantic understanding (AI/NLP) to distinguish "table" from "chairs"; "et" (and) too common in material descriptions

**User action:** Manually verify mixed furniture sets

---

#### 3. Source Data Quality
**Issue:** Typos/spacing in dimensions

**Example:**
- "36, 5×28,5cm" (space after comma) → parses incorrectly

**Why accepted:** Allowing spaces after commas creates false positives ("1960, 5 items")

**User action:** Manually enter correct dimensions

---

## Troubleshooting

### Error: "FileNotFoundError"
**Cause:** Input file not found
**Solution:** 
1. Verify filename in script matches your Excel file
2. Ensure file is in same directory as script
3. Check file extension is `.xlsx`

### Error: "KeyError: 'LOT'" or "KeyError: 'TYPESET'"
**Cause:** Required columns missing or misspelled
**Solution:**
1. Open Excel file
2. Verify column headers are exactly `LOT` and `TYPESET` (case-sensitive)
3. No extra spaces in column names

### Output: All items classified as 3D
**Cause:** Material keywords not recognized (language/spelling mismatch)
**Solution:**
1. Check if descriptions use French/English terms not in material list
2. Add missing terms to `true_2d_materials` list (see Configuration)

### Output: Weird dimension values (e.g., D=1960)
**Cause:** Script extracting dates or other numbers as dimensions
**Solution:**
1. Check `PROCESSING_FLAGS` for clues
2. If systematic issue, report for script enhancement
3. Manually correct affected lots

### Console: "Progress: 500/1000" then hangs
**Cause:** Possible infinite loop on specific lot description
**Solution:**
1. Note which lot number caused issue
2. Remove that lot temporarily
3. Report issue with lot description for debugging

---

## Configuration

### Customizable Settings

#### 1. Input/Output Filenames
**Location:** Lines ~593-600
```python
# INPUT
df = pd.read_excel('YOUR_INPUT_FILE.xlsx')

# OUTPUT
filename = 'YOUR_OUTPUT_FILE.xlsx'
```

#### 2. Default 2D Depth
**Location:** Line ~58 and processing sections
```python
result[f'D_{i}'] = 5.0  # Change 5.0 to desired default depth in cm
```

#### 3. High Count Threshold
**Location:** Item count detection section
```python
if item_count > 10:  # Change 10 to desired threshold
```

#### 4. Material Keywords (Add Missing Terms)
**Location:** Lines ~40-53
```python
self.true_2d_materials = [
    # Add your materials here
    'your_new_material_keyword',
]
```

**Example additions:**
- French art techniques: 'monotype', 'frottage', 'grattage'
- Regional terminology: 'offset', 'heliogravure'
- Specific media: 'cyanotype', 'albumine'

### DO NOT MODIFY

**Core logic sections:**
- Dimension extraction patterns (lines ~28-38)
- Classification logic (lines ~150-250)
- Dimension processing rules (lines ~350-500)

**Modifying these risks:**
- Breaking existing functionality
- Creating false positives/negatives
- Inconsistent processing

---

## Support & Maintenance

### Adding New Material Keywords
When you encounter materials not recognized:

1. Identify the keyword from lot description
2. Add to appropriate list:
   - `true_2d_materials` for flat artworks
   - `assemblage_keywords` for 3D assemblages
   - `material_keywords` for material extraction
3. Test with sample data
4. Document additions

### Reporting Issues
When reporting problems, include:
- Exact lot description (TYPESET value)
- Expected output
- Actual output
- Processing flags and logs

---

## Quick Reference Card

### Input Checklist
- [ ] Excel file (.xlsx)
- [ ] Contains `LOT` column
- [ ] Contains `TYPESET` column
- [ ] Filename updated in script
- [ ] Dependencies installed

### Output Quality Checks
- [ ] Total lots processed matches input
- [ ] Manual review % reasonable (~10-20%)
- [ ] 2D items have D=5
- [ ] 3D items have complete H, L, D
- [ ] Flags make sense for flagged items

### Common Tasks
| Task | How To |
|------|--------|
| Filter manual review | `MANUAL_REVIEW_REQUIRED = TRUE` |
| Find incomplete dimensions | Check for empty L or D columns |
| See processing details | Read `CONVERSION_LOG` column |
| Understand flags | Reference flags table above |

---

**Last Updated:** [Current Date]  
**Script Version:** Final Release  
**Contact:** [Your Contact Info]
