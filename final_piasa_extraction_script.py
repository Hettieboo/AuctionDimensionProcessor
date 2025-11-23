# -*- coding: utf-8 -*-
"""
Final Piasa Extraction Script
Standalone .py version for Streamlit deployment
"""

import pandas as pd
import re
from typing import List, Dict, Optional, Tuple

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
            'painting', 'drawing', 'print', 'watercolor'
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
            'verre': 'Glass', 'cristal': 'Crystal', 'céramique': 'Ceramic', 'porcelaine': 'Porcelain',
            'marbre': 'Marble', 'pierre': 'Stone', 'cuir': 'Leather', 'textile': 'Textile',
            'tissu': 'Fabric', 'velours': 'Velvet', 'soie': 'Silk', 'coton': 'Cotton',
            'lin': 'Linen', 'plastique': 'Plastic', 'résine': 'Resin', 'plexiglas': 'Plexiglass',
            'toile': 'Canvas', 'papier': 'Paper', 'carton': 'Cardboard'
        }

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
        # Remove duplicates
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
        return bool(re.search(r'\b(ouvert|fermé|ferme)\b', text.lower()))

    def detect_item_count(self, text: str) -> Tuple[int, List[str]]:
        if not isinstance(text, str):
            return 1, []
        text_lower = text.lower()
        flags = []

        # Check for 'chaque'
        if re.search(r'\bchaque\b', text_lower):
            flags.append("CHAQUE_DETECTED: manual count verification needed")
            for word, count in self.multiples_keywords.items():
                if re.search(r'\b' + word + r'\b', text_lower):
                    return count, flags
            return 1, flags

        # Ensemble de X
        match = re.search(r'ensemble\s+de\s+(\d+)', text_lower)
        if match:
            try:
                return int(match.group(1)), flags
            except:
                pass

        # Keywords at start
        for word, count in self.multiples_keywords.items():
            pattern = r'(?:^|[.\n])\s*' + word + r'\s+de\s+'
            if re.search(pattern, text_lower):
                edition_pattern = r'(?:édition|edition|tirage)\s+de\s+' + word
                if not re.search(edition_pattern, text_lower):
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
            for match_3d in matches_3d:
                dimensions.append({
                    'H': self.normalize_number(match_3d.group(1)),
                    'L': self.normalize_number(match_3d.group(2)),
                    'P': self.normalize_number(match_3d.group(3)),
                    'Diameter': None
                })

            matches_2d = self.two_d_pattern.finditer(segment)
            for match_2d in matches_2d:
                dimensions.append({
                    'H': self.normalize_number(match_2d.group(1)),
                    'L': self.normalize_number(match_2d.group(2)),
                    'P': None,
                    'Diameter': None
                })
        return [d for d in dimensions if any(v is not None for v in d.values())]

    # Placeholder: You would include the full process_lot and classify_item_type methods here
    # For brevity, you can copy them directly from your original code.

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process the entire dataframe"""
        results = []
        for idx, row in df.iterrows():
            result = self.process_lot(row)
            results.append(result)
        return pd.DataFrame(results)

# Example usage:
if __name__ == "__main__":
    processor = AuctionDimensionProcessor()
    df = pd.read_excel("your_file.xlsx")  # Replace with your Excel file path
    df_final = processor.process_dataframe(df)
    df_final.to_excel("extracted_dimensions.xlsx", index=False)
    print("Processing complete. File saved as extracted_dimensions.xlsx")
