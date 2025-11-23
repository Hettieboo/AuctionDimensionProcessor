# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import re
from typing import List, Dict, Optional, Tuple

# --- Page config ---
st.set_page_config(page_title="📦 Piasa Auction Dimension Processor", layout="wide")
st.title("📦 Piasa Auction Dimension Processor")
st.markdown("Upload your Excel file and process auction lot dimensions automatically.")

# --- AuctionDimensionProcessor class ---
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
            'cuivre': 'Copper', 'laiton': 'Brass', 'bronze': 'Bronze', 'fer': 'Iron', 'acier': 'Steel',
            'aluminium': 'Aluminum', 'métal': 'Metal', 'metal': 'Metal', 'bois': 'Wood', 'chêne': 'Oak',
            'noyer': 'Walnut', 'teck': 'Teak', 'palissandre': 'Rosewood', 'ébène': 'Ebony', 'châtaignier': 'Chestnut',
            'verre': 'Glass', 'cristal': 'Crystal', 'céramique': 'Ceramic', 'porcelaine': 'Porcelain',
            'grès': 'Stoneware', 'faïence': 'Earthenware', 'marbre': 'Marble', 'pierre': 'Stone', 'granit': 'Granite',
            'cuir': 'Leather', 'textile': 'Textile', 'tissu': 'Fabric', 'velours': 'Velvet', 'soie': 'Silk',
            'coton': 'Cotton', 'lin': 'Linen', 'plastique': 'Plastic', 'résine': 'Resin', 'plexiglas': 'Plexiglass',
            'toile': 'Canvas', 'papier': 'Paper', 'carton': 'Cardboard'
        }

    def normalize_number(self, num_str: str) -> Optional[float]:
        if not num_str:
            return None
        try:
            return float(num_str.replace(',', '.'))
        except:
            return None

    # Add the rest of the methods (extract_material, should_skip_lot, detect_item_count, 
    # extract_dimensions, classify_item_type, process_lot, process_dataframe) exactly as in your original code.
    # For brevity, not repeated here, but you should paste them from your original script.

# --- Streamlit file uploader ---
st.sidebar.header("Upload Excel File")
uploaded_file = st.sidebar.file_uploader("Choose your Excel file", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        st.sidebar.success(f"Loaded {len(df)} rows successfully!")

        processor = AuctionDimensionProcessor()
        with st.spinner("Processing lots..."):
            df_final = processor.process_dataframe(df)

        st.success("Processing completed!")

        st.dataframe(df_final.head(20))  # Preview first 20 rows

        # Download button
        csv = df_final.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name='extracted_dimensions.csv',
            mime='text/csv'
        )
    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Please upload an Excel file to start processing.")
