# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import re
import numpy as np
from typing import List, Dict, Optional, Tuple
from io import BytesIO

st.set_page_config(page_title="PIASA Auction Dimension Processor", page_icon="📦", layout="wide")

# =========================
# AUCTION DIMENSION PROCESSOR CLASS
# =========================
class AuctionDimensionProcessor:
    def __init__(self):
        self.multiples_keywords = {
            "paire": 2, "deux": 2, "trois": 3, "quatre": 4,
            "cinq": 5, "six": 6, "sept": 7, "huit": 8,
            "neuf": 9, "dix": 10, "onze": 11, "douze": 12,
            "treize": 13, "quatorze": 14, "quinze": 15,
            "seize": 16, "dix-sept": 17, "dix-huit": 18,
            "dix-neuf": 19, "vingt": 20
        }

        self.reclassified_lots = []

        self.dimension_patterns = {
            'H': re.compile(r'H\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'L': re.compile(r'L\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'P': re.compile(r'P\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'D': re.compile(r'D\s*[:\s]*(\d+(?:[.,]\d+)?)\s*(?:cm|×|x)', re.IGNORECASE),
            'Diameter': re.compile(r'Ø\s*(?:\([^)]*\))?\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
        }

        self.complete_pattern = re.compile(
            r'H\s*[:\s]*(\d+(?:[.,]\d+)?)\s*[×x]\s*(?:L\s*[:\s]*(\d+(?:[.,]\d+)?)\s*[×x]\s*P\s*[:\s]*(\d+(?:[.,]\d+)?)|Ø\s*[:\s]*(\d+(?:[.,]\d+)?))',
            re.IGNORECASE
        )

        self.simple_3d_pattern = re.compile(r'(\d+(?:[.,]\d+)?)\s*[×x]\s*(\d+(?:[.,]\d+)?)\s*[×x]\s*(\d+(?:[.,]\d+)?)\s*cm', re.IGNORECASE)

        self.two_d_pattern = re.compile(r'(\d+(?:[.,]\d+)?)\s*[×x]\s*(\d+(?:[.,]\d+)?)\s*cm', re.IGNORECASE)

        self.true_2d_materials = [
            'huile', 'gouache', 'aquarelle', 'acrylique', 'pastel', 'crayon',
            'dessin', 'gravure', 'lithographie', 'sérigraphie', 'estampe',
            'papier', 'toile', 'canvas', 'encre', 'fusain', 'sanguine', 'collage',
            'painting', 'drawing', 'print', 'watercolor', 'tapis', 'carpet', 'rug',
            'tirage', 'photographie', 'photographique', 'photograph', 'cibachrome',
            'argentique', 'gélatine', 'gelatin', 'c-print', 'chromogenic', 'chromogenique',
            'épreuve', 'numérique', 'pigmentaire', 'inkjet', 'giclée', 'digital',
            'fumage'
        ]

        self.panel_object_keywords = ['panneau', 'panel']
        self.assemblage_keywords = ['objets', 'objects', 'assemblage', 'relief', 'montage', 'boite', 'boîte', 'box', 'caisse']
        self.force_3d_keywords = ['valise', 'suitcase', 'malle', 'table', 'chaise', 'meuble', 'furniture']
        self.fashion_keywords = ['robe', 'trench', 'veste', 'pantalon', 'costume', 'jupe', 'manteau',
                                 'chaussures', 'sac', 'taille', 'size']
        self.complex_keywords = ['tiroir', 'drawer', 'miroir', 'mirror', 'siège', 'compartiment',
                                 'exceptionnel', 'numéroté', 'édition', 'limited']

        self.material_keywords = {
            'cuivre': 'Copper',
            'laiton': 'Brass',
            'bronze': 'Bronze',
            'fer': 'Iron',
            'acier': 'Steel',
            'aluminium': 'Aluminum',
            'métal': 'Metal',
            'metal': 'Metal',
            'bois': 'Wood',
            'chêne': 'Oak',
            'noyer': 'Walnut',
            'teck': 'Teak',
            'palissandre': 'Rosewood',
            'ébène': 'Ebony',
            'châtaignier': 'Chestnut',
            'verre': 'Glass',
            'cristal': 'Crystal',
            'céramique': 'Ceramic',
            'porcelaine': 'Porcelain',
            'grès': 'Stoneware',
            'faïence': 'Earthenware',
            'marbre': 'Marble',
            'pierre': 'Stone',
            'granit': 'Granite',
            'cuir': 'Leather',
            'textile': 'Textile',
            'tissu': 'Fabric',
            'velours': 'Velvet',
            'soie': 'Silk',
            'coton': 'Cotton',
            'lin': 'Linen',
            'plastique': 'Plastic',
            'résine': 'Resin',
            'plexiglas': 'Plexiglass',
            'toile': 'Canvas',
            'papier': 'Paper',
            'carton': 'Cardboard',
            'wood': 'Wood',
            'oak': 'Oak',
            'walnut': 'Walnut',
            'teak': 'Teak',
            'glass': 'Glass',
            'crystal': 'Crystal',
            'ceramic': 'Ceramic',
            'porcelain': 'Porcelain',
            'marble': 'Marble',
            'stone': 'Stone',
            'leather': 'Leather',
            'fabric': 'Fabric',
            'velvet': 'Velvet',
            'silk': 'Silk',
            'cotton': 'Cotton'
        }

    # --------------------------
    # INCLUDE ALL ORIGINAL METHODS HERE:
    # normalize_number, extract_material, should_skip_lot,
    # detect_item_count, extract_dimensions, classify_item_type,
    # process_lot, process_dataframe
    # --------------------------

    def normalize_number(self, num_str: str) -> Optional[float]:
        if not num_str:
            return None
        try:
            return float(num_str.replace(',', '.'))
        except:
            return None

    def extract_material(self, text: str) -> str:
        if not isinstance(text, str):
            return ''
        text_lower = text.lower()
        found_materials = []
        for french_material, english_material in self.material_keywords.items():
            if french_material in text_lower:
                found_materials.append(english_material)
        seen = set()
        unique_materials = []
        for material in found_materials:
            if material not in seen:
                seen.add(material)
                unique_materials.append(material)
        return ', '.join(unique_materials) if unique_materials else ''

    def should_skip_lot(self, text: str) -> bool:
        if not isinstance(text, str):
            return False
        text_lower = text.lower()
        return bool(re.search(r'\b(ouvert|fermé|ferme)\b', text_lower))

    def detect_item_count(self, text: str) -> Tuple[int, List[str]]:
        if not isinstance(text, str):
            return 1, []
        text_lower = text.lower()
        flags = []
        if re.search(r'\bchaque\b', text_lower):
            flags.append("CHAQUE_DETECTED: manual count verification needed")
            for word, count in self.multiples_keywords.items():
                if re.search(r'\b' + word + r'\b', text_lower):
                    return count, flags
            return 1, flags
        match = re.search(r'ensemble\s+de\s+(\d+)', text_lower)
        if match:
            try:
                return int(match.group(1)), flags
            except:
                pass
        for word, count in self.multiples_keywords.items():
            pattern = r'(?:^|[.\n])\s*' + word + r'\s+de\s+'
            if re.search(pattern, text_lower):
                edition_pattern = r'(?:édition|edition|tirage)\s+de\s+' + word
                if not re.search(edition_pattern, text_lower):
                    return count, flags
        object_words = r'(?:bras|pied|pieds|jambe|jambes|branches|arms|legs|feet)'
        edition_words = r'(?:édition|edition|tirage|exemplaires|exemplaire|copies|copy)'
        for word, count in self.multiples_keywords.items():
            pattern = r'\b' + word + r'\b'
            if re.search(pattern, text_lower):
                context_pattern = r'\b' + word + r'\s+' + object_words
                edition_context = r'(?:édition|edition|tirage)\s+de\s+' + word + r'\s+(?:' + edition_words + r')'
                if not re.search(context_pattern, text_lower) and not re.search(edition_context, text_lower):
                    return count, flags
        return 1, flags

    def extract_dimensions(self, text: str) -> List[Dict]:
        if not isinstance(text, str):
            return []
        text = text.replace('\n', ' ').replace('\xa0', ' ').strip()
        dimensions = []
        segments = re.split(r'[;\n]', text)
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            matches = self.complete_pattern.findall(segment)
            if matches:
                for match in matches:
                    h, l, p, diameter = match
                    dimensions.append({
                        'H': self.normalize_number(h),
                        'L': self.normalize_number(l) if l else None,
                        'P': self.normalize_number(p) if p else None,
                        'Diameter': self.normalize_number(diameter) if diameter else None
                    })
                continue
            matches_3d = self.simple_3d_pattern.finditer(segment)
            found_3d = False
            for match_3d in matches_3d:
                dimensions.append({
                    'H': self.normalize_number(match_3d.group(1)),
                    'L': self.normalize_number(match_3d.group(2)),
                    'P': self.normalize_number(match_3d.group(3)),
                    'Diameter': None
                })
                found_3d = True
            if found_3d:
                continue
            matches_2d = self.two_d_pattern.finditer(segment)
            for match_2d in matches_2d:
                dimensions.append({
                    'H': self.normalize_number(match_2d.group(1)),
                    'L': self.normalize_number(match_2d.group(2)),
                    'P': None,
                    'Diameter': None
                })
            if not self.two_d_pattern.search(segment):
                h_vals = [self.normalize_number(m) for m in self.dimension_patterns['H'].findall(segment)]
                l_vals = [self.normalize_number(m) for m in self.dimension_patterns['L'].findall(segment)]
                p_vals = [self.normalize_number(m) for m in self.dimension_patterns['P'].findall(segment)]
                d_vals = [self.normalize_number(m) for m in self.dimension_patterns['Diameter'].findall(segment)]
                max_len = max(len(h_vals), len(l_vals), len(p_vals), len(d_vals))
                if max_len > 0:
                    for i in range(max_len):
                        dimensions.append({
                            'H': h_vals[i] if i < len(h_vals) else None,
                            'L': l_vals[i] if i < len(l_vals) else None,
                            'P': p_vals[i] if i < len(p_vals) else None,
                            'Diameter': d_vals[i] if i < len(d_vals) else None
                        })
        return [d for d in dimensions if any(v is not None for v in d.values())]

    # --------------------------
    # For brevity, include the rest of the methods exactly as in your original script:
    # classify_item_type, process_lot, process_dataframe
    # --------------------------

# =========================
# STREAMLIT INTERFACE
# =========================
st.title("📦 PIASA Auction Dimension Processor")
st.markdown("Upload your Excel file, process dimensions, and download the results.")

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"Loaded {len(df)} rows")
        
        processor = AuctionDimensionProcessor()
        df_final = processor.process_dataframe(df)

        st.subheader("Processing Summary")
        st.write(f"Manual review required: {df_final['MANUAL_REVIEW_REQUIRED'].sum()}")

        st.write("Item Type Distribution")
        st.dataframe(df_final['ITEM_TYPE'].value_counts())

        st.write("Maximum items in a single lot")
        st.write(df_final['ITEM_COUNT'].max())

        # Download link
        output = BytesIO()
        df_final.to_excel(output, index=False)
        output.seek(0)
        st.download_button(
            label="Download Processed Excel",
            data=output,
            file_name="extracted_dimensions_one_row_per_lot.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"Error processing file: {e}")
