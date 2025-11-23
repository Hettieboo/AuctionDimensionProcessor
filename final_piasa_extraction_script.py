# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import re
from typing import List, Dict, Optional, Tuple
from io import BytesIO

# -----------------------------------------
# AuctionDimensionProcessor Class
# -----------------------------------------
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
            'cuivre': 'Copper', 'laiton': 'Brass', 'bronze': 'Bronze', 'fer': 'Iron',
            'acier': 'Steel', 'aluminium': 'Aluminum', 'métal': 'Metal', 'metal': 'Metal',
            'bois': 'Wood', 'chêne': 'Oak', 'noyer': 'Walnut', 'teck': 'Teak',
            'palissandre': 'Rosewood', 'ébène': 'Ebony', 'châtaignier': 'Chestnut',
            'verre': 'Glass', 'cristal': 'Crystal', 'céramique': 'Ceramic',
            'porcelaine': 'Porcelain', 'grès': 'Stoneware', 'faïence': 'Earthenware',
            'marbre': 'Marble', 'pierre': 'Stone', 'granit': 'Granite', 'cuir': 'Leather',
            'textile': 'Textile', 'tissu': 'Fabric', 'velours': 'Velvet', 'soie': 'Silk',
            'coton': 'Cotton', 'lin': 'Linen', 'plastique': 'Plastic', 'résine': 'Resin',
            'plexiglas': 'Plexiglass', 'toile': 'Canvas', 'papier': 'Paper',
            'carton': 'Cardboard', 'wood': 'Wood', 'oak': 'Oak', 'walnut': 'Walnut',
            'teak': 'Teak', 'glass': 'Glass', 'crystal': 'Crystal', 'ceramic': 'Ceramic',
            'porcelain': 'Porcelain', 'marble': 'Marble', 'stone': 'Stone',
            'leather': 'Leather', 'fabric': 'Fabric', 'velvet': 'Velvet', 'silk': 'Silk',
            'cotton': 'Cotton'
        }

    # -------------------------
    # Helper Methods
    # -------------------------
    def normalize_number(self, s: str) -> Optional[float]:
        try:
            return float(s.replace(',', '.'))
        except:
            return None

    def extract_material(self, text: str) -> Optional[str]:
        for k, v in self.material_keywords.items():
            if k.lower() in text.lower():
                return v
        return None

    def should_skip_lot(self, text: str) -> bool:
        skip_keywords = ['lot', 'collection', 'ensemble']
        return any(k.lower() in text.lower() for k in skip_keywords)

    def detect_item_count(self, text: str) -> int:
        for k, v in self.multiples_keywords.items():
            if k in text.lower():
                return v
        return 1

    def extract_dimensions(self, text: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        match = self.simple_3d_pattern.search(text)
        if match:
            return tuple(self.normalize_number(dim) for dim in match.groups())
        match = self.two_d_pattern.search(text)
        if match:
            h, l = match.groups()
            return self.normalize_number(h), self.normalize_number(l), None
        return None, None, None

    def classify_item_type(self, text: str) -> str:
        text_lower = text.lower()
        if any(k in text_lower for k in self.panel_object_keywords + self.assemblage_keywords + self.force_3d_keywords):
            return '3D'
        if any(k in text_lower for k in self.true_2d_materials):
            return '2D'
        return 'MANUAL_CHECK'

    def process_lot(self, lot: pd.Series) -> Dict:
        typeset = str(lot.get('TYPESET', ''))
        material = self.extract_material(typeset)
        h, l, p = self.extract_dimensions(typeset)
        item_type = self.classify_item_type(typeset)
        count = self.detect_item_count(typeset)
        manual_review = item_type == 'MANUAL_CHECK'
        return {
            'H': h, 'L': l, 'P': p, 'MATERIAL': material,
            'ITEM_TYPE': item_type, 'COUNT': count, 'MANUAL_REVIEW_REQUIRED': manual_review
        }

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        results = df.apply(lambda row: pd.Series(self.process_lot(row)), axis=1)
        df_final = pd.concat([df, results], axis=1)
        return df_final

# -------------------------
# Streamlit App Starts Here
# -------------------------
st.set_page_config(page_title="Piasa Auction Dimension Processor", layout="wide")
st.title("Piasa Auction Dimension Processor")

st.markdown("""
Upload an Excel file with a 'TYPESET' column. The app will process dimensions for each lot,
classify items as 2D/3D/MANUAL_CHECK, and allow you to download the processed Excel file.
""")

uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"Loaded {len(df)} rows")
        processor = AuctionDimensionProcessor()

        with st.spinner("Processing lots..."):
            df_final = processor.process_dataframe(df)

        st.success("Processing complete!")

        # Show a preview of processed data
        st.dataframe(df_final.head(10))

        # Download button
        output = BytesIO()
        df_final.to_excel(output, index=False)
        output.seek(0)

        st.download_button(
            label="Download Processed Excel",
            data=output,
            file_name="extracted_dimensions_one_row_per_lot.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown(f"Manual review required: {df_final['MANUAL_REVIEW_REQUIRED'].sum()} lots")

    except Exception as e:
        st.error(f"Error processing file: {e}")
