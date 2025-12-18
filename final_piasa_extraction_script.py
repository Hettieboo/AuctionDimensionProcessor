# auction_processor_app_full.py
import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
import plotly.express as px

# ----------------- Enhanced Auction Dimension Extractor -----------------
class AuctionDimensionExtractor:
    def __init__(self):
        # Map words to numbers for multiples
        self.multiples_keywords = {
            "paire":2, "deux":2, "trois":3, "quatre":4, "cinq":5,
            "six":6, "sept":7, "huit":8, "neuf":9, "dix":10
        }
        # Dimension patterns
        self.dimension_patterns = {
            'H': re.compile(r'H\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'L': re.compile(r'L\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'P': re.compile(r'P\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'Diameter': re.compile(r'Ø\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE)
        }

    def normalize_number(self, num_str):
        if not num_str:
            return None
        try:
            return float(num_str.replace(',','.'))
        except:
            return None

    def detect_multiples(self, text):
        if not isinstance(text,str): return 1
        text_lower = text.lower()
        for word,num in self.multiples_keywords.items():
            if word in text_lower:
                return num
        m = re.search(r'ensemble\s+de\s+(\d+)', text_lower)
        if m:
            return int(m.group(1))
        return 1

    def detect_item_type(self, text):
        if not isinstance(text,str): return '3D'
        text_lower = text.lower()
        # 2D keywords
        keywords_2d = ['huile','acrylique','aquarelle','pastel','dessin','gravure','lithographie','sérigraphie']
        if any(k in text_lower for k in keywords_2d):
            return '2D'
        h = self.dimension_patterns['H'].search(text)
        l = self.dimension_patterns['L'].search(text)
        p = self.dimension_patterns['P'].search(text)
        if h and l and not p:
            return '2D'
        return '3D'

    def extract_dimensions(self, text):
        dims = {}
        for key, pattern in self.dimension_patterns.items():
            match = pattern.search(text)
            dims[key] = self.normalize_number(match.group(1)) if match else None
        return dims

    def process_dataframe(self, df, column='TYPESET'):
        result_rows = []
        for _, row in df.iterrows():
            text = str(row.get(column,''))

            multiples = self.detect_multiples(text)
            item_type = self.detect_item_type(text)
            dims = self.extract_dimensions(text)

            for _ in range(multiples):
                new_row = row.copy()
                new_row.update(dims)
                new_row['ITEM_TYPE'] = item_type
                new_row['ITEM_COUNT'] = multiples
                result_rows.append(new_row)
        return pd.DataFrame(result_rows)

    def shipping_standardization(self, df):
        df = df.copy()
        df['CONVERSION_LOG'] = ''
        for idx, row in df.iterrows():
            conv = []
            if row['ITEM_TYPE']=='2D':
                h_val = row.get('H') or 0
                l_val = row.get('L') or 0
                if h_val and l_val:
                    df.at[idx,'H'] = min(h_val,l_val)
                    df.at[idx,'L'] = max(h_val,l_val)
                    conv.append("2D: L=max(H,L)")
                df.at[idx,'D'] = 5.0
            else:
                diameter = row.get('Diameter')
                if diameter:
                    df.at[idx,'L'] = diameter
                    df.at[idx,'D'] = diameter
                    conv.append("3D: D=Diameter")
            df.at[idx,'CONVERSION_LOG'] = "; ".join(conv)
        return df

# ----------------- Streamlit App -----------------
st.set_page_config(page_title="Auction Dimension Processor", page_icon="📦", layout="wide")

# Custom CSS
st.markdown("""
<style>
.stApp {background: linear-gradient(135deg,#FFDDAA,#FF77AA);}
h1 {text-align:center;color:#333;}
.metric-card {background:white;padding:20px;border-radius:10px;margin:10px 0;box-shadow:0 4px 8px rgba(0,0,0,0.1);}
.stButton>button {background:#FF77AA;color:white;font-weight:bold;border-radius:8px;}
</style>
""", unsafe_allow_html=True)

# Header
st.title("📦 Auction Dimension Processor")
st.markdown("### Transform auction data with precision and style")

# Sidebar
with st.sidebar:
    st.markdown("## 📄 About")
    st.info("Upload Excel files with auction lots. The processor extracts dimensions, detects 2D/3D, handles multiples, standardizes for shipping, and provides metrics & visuals.")

# File upload
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ Loaded {len(df):,} rows!")

        # Process
        processor = AuctionDimensionExtractor()
        df_processed = processor.process_dataframe(df)
        df_shipping = processor.shipping_standardization(df_processed)

        # Metrics
        total_items = len(df_shipping)
        n2d = (df_shipping['ITEM_TYPE']=='2D').sum()
        n3d = (df_shipping['ITEM_TYPE']=='3D').sum()
        converted = (df_shipping['CONVERSION_LOG'] != '').sum()

        st.markdown("## 📊 Key Metrics")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Items", f"{total_items:,}")
        col2.metric("2D Items", f"{n2d:,}")
        col3.metric("3D Items", f"{n3d:,}")
        col4.metric("Converted Rows", f"{converted:,}")

        # Filters
        st.markdown("## ⚡ Filters")
        types_selected = st.multiselect("Filter by ITEM_TYPE", options=['2D','3D'], default=['2D','3D'])
        df_filtered = df_shipping[df_shipping['ITEM_TYPE'].isin(types_selected)]

        # Safe row highlighting
        def highlight_row(row):
            if 'ITEM_TYPE' not in row.index: return ['']*len(row)
            if row['ITEM_TYPE']=='2D': return ['background-color:#FFDDEE']*len(row)
            if row['ITEM_TYPE']=='3D': return ['background-color:#DDEEFF']*len(row)
            return ['']*len(row)

        st.markdown("## 🔍 Data Preview")
        st.dataframe(df_filtered.style.apply(highlight_row, axis=1), height=400)

        # Download
        output = BytesIO()
        df_filtered.to_excel(output, index=False)
        output.seek(0)
        st.download_button(
            "⬇️ Download Processed Excel",
            data=output,
            file_name=f"processed_auction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )

        # Pie chart
        st.markdown("## 📈 Item Type Distribution")
        if not df_filtered.empty:
            fig = px.pie(df_filtered, names='ITEM_TYPE', values='ITEM_COUNT',
                         color='ITEM_TYPE', color_discrete_map={'2D':'#FF77AA','3D':'#77CCFF'})
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
else:
    st.info("👆 Upload an Excel file to start processing.")
