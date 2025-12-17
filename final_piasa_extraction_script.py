# auction_processor_app.py
import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# ----------------- AuctionDimensionProcessor -----------------
class AuctionDimensionProcessor:
    def __init__(self):
        self.multiples_keywords = {
            "paire":2, "deux":2, "trois":3, "quatre":4, "cinq":5, "six":6,
            "sept":7, "huit":8, "neuf":9, "dix":10
        }
        self.dimension_patterns = {
            'H': re.compile(r'H\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'L': re.compile(r'L\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'P': re.compile(r'P\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE)
        }
    
    def normalize_number(self, num_str):
        if not num_str:
            return None
        try:
            return float(num_str.replace(',','.'))
        except:
            return None

    def detect_multiples(self, text):
        if not isinstance(text, str):
            return 1
        text = text.lower()
        for word, num in self.multiples_keywords.items():
            if word in text:
                return num
        m = re.search(r'ensemble\s+de\s+(\d+)', text)
        if m:
            return int(m.group(1))
        return 1

    def detect_item_type(self, text):
        if not isinstance(text, str):
            return '3D'
        text = text.lower()
        if any(k in text for k in ['huile','acrylique','aquarelle','pastel','dessin','gravure']):
            return '2D'
        h = self.dimension_patterns['H'].search(text)
        l = self.dimension_patterns['L'].search(text)
        p = self.dimension_patterns['P'].search(text)
        if h and l and not p:
            return '2D'
        return '3D'

    def extract_dimensions(self, text):
        h = self.dimension_patterns['H'].search(text)
        l = self.dimension_patterns['L'].search(text)
        p = self.dimension_patterns['P'].search(text)
        return {
            'H': self.normalize_number(h.group(1)) if h else None,
            'L': self.normalize_number(l.group(1)) if l else None,
            'P': self.normalize_number(p.group(1)) if p else None
        }

    def process_dataframe(self, df, column='TYPESET'):
        rows = []
        for _, row in df.iterrows():
            text = str(row.get(column, ''))
            count = self.detect_multiples(text)
            item_type = self.detect_item_type(text)
            dims = self.extract_dimensions(text)
            for _ in range(count):
                new_row = row.copy()
                new_row.update(dims)
                new_row['ITEM_TYPE'] = item_type
                new_row['ITEM_COUNT'] = count
                rows.append(new_row)
        df_final = pd.DataFrame(rows)
        return df_final

# ----------------- Streamlit App -----------------
st.set_page_config(page_title="Auction Dimension Processor", page_icon="📦", layout="wide")

st.markdown("""
<style>
.stApp {background: linear-gradient(135deg,#FFDDAA,#FF77AA);}
h1 {text-align:center;color:#333;}
.metric-card {background:white;padding:20px;border-radius:10px;margin:10px 0;box-shadow:0 4px 8px rgba(0,0,0,0.1);}
.stButton>button {background:#FF77AA;color:white;font-weight:bold;border-radius:8px;}
</style>
""", unsafe_allow_html=True)

st.title("📦 Auction Dimension Processor")
st.markdown("### Transform auction data with precision and style")

# Sidebar
with st.sidebar:
    st.markdown("## 📄 About")
    st.info("Upload Excel files with auction lots. The processor extracts dimensions, detects 2D/3D, and gives real-time metrics.")

# Upload
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success(f"✅ Loaded {len(df):,} rows!")
    
    processor = AuctionDimensionProcessor()
    df_final = processor.process_dataframe(df)
    
    # Metrics
    total_items = len(df_final)
    n2d = (df_final['ITEM_TYPE']=='2D').sum()
    n3d = (df_final['ITEM_TYPE']=='3D').sum()
    
    st.markdown("## 📊 Key Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Items", f"{total_items:,}")
    col2.metric("2D Items", f"{n2d:,}")
    col3.metric("3D Items", f"{n3d:,}")
    
    # Filters
    st.markdown("## ⚡ Filters")
    types_selected = st.multiselect("Filter by ITEM_TYPE", options=['2D','3D'], default=['2D','3D'])
    df_filtered = df_final[df_final['ITEM_TYPE'].isin(types_selected)]
    
    # Highlight rows safely
    def highlight_row(row):
        if 'ITEM_TYPE' not in row.index:
            return ['']*len(row)
        if row['ITEM_TYPE']=='2D':
            return ['background-color:#FFDDEE']*len(row)
        if row['ITEM_TYPE']=='3D':
            return ['background-color:#DDEEFF']*len(row)
        return ['']*len(row)
    
    st.markdown("## 🔍 Data Preview")
    st.dataframe(df_filtered.style.apply(highlight_row, axis=1), height=400)
    
    # Download
    output = BytesIO()
    df_filtered.to_excel(output, index=False)
    output.seek(0)
    st.download_button("⬇️ Download Excel", data=output, file_name=f"processed_auction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    
    # Optional visual
    st.markdown("## 📈 Visualizations")
    fig = px.pie(df_filtered, names='ITEM_TYPE', title="Item Type Distribution", color='ITEM_TYPE', color_discrete_map={'2D':'#FF77AA','3D':'#77CCFF'})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("👆 Upload an Excel file to start processing.")
