# -*- coding: utf-8 -*-
"""
Plain Piasa Auction Dimension Processor
Standalone .py version
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

    def normalize_number(self, num_str: str) -> Optional[float]:
        if not num_str:
            return None
        try:
            return float(num_str.replace(',', '.'))
        except:
            return None

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

    def process_lot(self, row: pd.Series) -> Dict:
        text = row.get('Description', '')
        dimensions = self.extract_dimensions(text)
        return {
            'LotNumber': row.get('LotNumber', None),
            'Dimensions': dimensions
        }

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        results = []
        for idx, row in df.iterrows():
            result = self.process_lot(row)
            results.append(result)
        return pd.DataFrame(results)

# Example usage
if __name__ == "__main__":
    processor = AuctionDimensionProcessor()
    df = pd.read_excel("your_file.xlsx")  # Replace with your Excel file
    df_final = processor.process_dataframe(df)
    df_final.to_excel("extracted_dimensions.xlsx", index=False)
    print("Processing complete. File saved as extracted_dimensions.xlsx")
