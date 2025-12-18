# auction_processor_app.py
import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# Auction Dimension Extractor
# -----------------------------
class AuctionDimensionExtractor:
    def __init__(self):
        self.multiples_keywords = {
            "paire": 2, "deux": 2, "trois": 3, "quatre": 4,
            "cinq": 5, "six": 6, "sept": 7, "huit": 8,
            "neuf": 9, "dix": 10
        }
        self.dimension_patterns = {
            'H': re.compile(r'H\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'L': re.compile(r'L\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'P': re.compile(r'P\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'Diameter': re.compile(r'Ø\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE)
        }

    def normalize_number(self, num_str):
        try:
            return float(str(num_str).replace(",", "."))
        except:
            return None

    def detect_multiples(self, text):
        text = str(text).lower()
        for word, count in self.multiples_keywords.items():
            if word in text:
                return count
        m = re.search(r'ensemble\s+de\s+(\d+)', text)
        if m:
            return int(m.group(1))
        return 1

    def detect_item_type(self, text):
        keywords_2d = [
            'huile', 'gouache', 'aquarelle', 'acrylique', 'pastel', 'crayon',
            'dessin', 'gravure', 'lithographie', 'sérigraphie', 'estampe',
            'papier', 'toile', 'canvas', 'carton', 'technique mixte',
            'oil', 'watercolor', 'acrylic', 'drawing', 'print', 'painting',
            'encre', 'fusain', 'sanguine', 'collage', 'mixed media'
        ]
        ignore_terms = ['provenance', 'bibliographie', 'catalogue', 'album', 'exposition', 'collection']
        text_lower = str(text).lower()[:300]
        if any(k in text_lower for k in keywords_2d) and not any(i in text_lower for i in ignore_terms):
            return '2D'
        return '3D'

    def extract_dimensions(self, text):
        dims = []
        for segment in re.split(r'[;\n]', str(text)):
            d = {'H': None, 'L': None, 'P': None, 'Diameter': None}
            for key, pattern in self.dimension_patterns.items():
                match = pattern.search(segment)
                d[key] = self.normalize_number(match.group(1)) if match else None
            dims.append(d)
        return dims

    def process_dataframe(self, df, typeset_col='TYPESET'):
        rows = []
        for _, row in df.iterrows():
            text = str(row.get(typeset_col, ''))
            multiples = self.detect_multiples(text)
            item_type = self.detect_item_type(text)
            dims_list = self.extract_dimensions(text)
            if len(dims_list) == 1 and multiples > 1:
                dims_list *= multiples
            elif len(dims_list) > 1 and multiples > len(dims_list):
                cycles = (multiples + len(dims_list) - 1) // len(dims_list)
                dims_list = (dims_list * cycles)[:multiples]
            for dims in dims_list:
                new_row = row.copy()
                new_row.update(dims)
                new_row['ITEM_TYPE'] = item_type
                new_row['ITEM_COUNT'] = multiples
                new_row['D'] = dims.get('Diameter') or dims.get('P') or dims.get('L')
                rows.append(new_row)
        return pd.DataFrame(rows)

def shipping_ready(df):
    df = df.copy()
    df['CONVERSION_LOG'] = ''
    for idx, row in df.iterrows():
        logs = []
        if row['ITEM_TYPE'] == '2D':
            logs.append("2D: L=max(H,L), D=5")
        else:
            if pd.notna(row.get('Diameter')):
                if row['L'] != row['Diameter']:
                    df.at[idx, 'L'] = row['Diameter']
                    logs.append("L=Ø")
                if row['D'] != row['Diameter']:
                    df.at[idx, 'D'] = row['Diameter']
                    logs.append("D=Ø")
        df.at[idx, 'CONVERSION_LOG'] = "; ".join(logs)
    return df

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Auction Dimension Processor", layout="wide", page_icon="📦")
st.markdown("""
    <style>
    .stApp {background: linear-gradient(135deg, #f9f9f9, #e0f7fa);}
    .header {text-align:center; font-size:42px; font-weight:bold; background: linear-gradient(135deg,#ff6f61,#1abc9c); -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
    .metric-card {background:white; padding:15px; border-radius:10px; box-shadow:0 4px 6px rgba(0,0,0,0.1);}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="header">📦 Auction Dimension Processor</div>', unsafe_allow_html=True)
st.markdown("### Transform auction data with precision and style")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/000000/auction.png", width=100)
    st.markdown("## 📊 About")
    st.info("""
    - Upload Excel auction data
    - Extract H, L, P, Diameter
    - Detect 2D/3D items and multiples
    - Prepare shipping-ready D values
    - Visualize metrics and download results
    """)
    typeset_col = st.text_input("TypeSet Column Name", value="TYPESET")
    show_shipping = st.checkbox("Show Shipping-Ready Data", value=True)
    st.markdown("---")

# File Upload
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success(f"✅ Loaded {len(df):,} rows")
    st.dataframe(df.head(5))

    # Processing
    extractor = AuctionDimensionExtractor()
    df_processed = extractor.process_dataframe(df, typeset_col)
    df_final = shipping_ready(df_processed) if show_shipping else df_processed

    # Metrics
    st.markdown("---")
    st.subheader("📊 Key Metrics")
    total_items = len(df_final)
    total_2d = len(df_final[df_final['ITEM_TYPE'] == '2D'])
    total_3d = len(df_final[df_final['ITEM_TYPE'] == '3D'])
    total_converted = len(df_final[df_final['CONVERSION_LOG'] != ''])
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Items", total_items)
    col2.metric("2D Items", total_2d)
    col3.metric("3D Items", total_3d)
    col4.metric("Converted Rows", total_converted)

    # Filters
    st.markdown("---")
    st.subheader("⚡ Filters")
    type_filter = st.multiselect("Filter by ITEM_TYPE", options=['2D','3D'], default=['2D','3D'])
    conversion_filter = st.checkbox("Show only converted rows")
    df_filtered = df_final[df_final['ITEM_TYPE'].isin(type_filter)]
    if conversion_filter:
        df_filtered = df_filtered[df_filtered['CONVERSION_LOG'] != '']

    # Charts
    st.markdown("---")
    st.subheader("📈 Visualizations")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(
            df_filtered, names='ITEM_TYPE', title="Item Type Distribution",
            color_discrete_map={'2D':'#FF6F61','3D':'#1ABC9C'}
        )
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        df_filtered['Converted'] = df_filtered['CONVERSION_LOG'].apply(lambda x: 0 if x=='' else 1)
        fig2 = px.histogram(df_filtered, x='D', color='ITEM_TYPE', nbins=20,
                            title="Distribution of D by ITEM_TYPE",
                            color_discrete_map={'2D':'#FF6F61','3D':'#1ABC9C'})
        st.plotly_chart(fig2, use_container_width=True)

    # Data table
    st.markdown("---")
    st.subheader("🔍 Data Preview")
    def highlight_row(row):
        if row['ITEM_TYPE']=='2D':
            return ['background-color:#FFEBE6']*len(row)
        elif row['ITEM_TYPE']=='3D':
            return ['background-color:#E0F7FA']*len(row)
        return ['']*len(row)
    st.dataframe(df_filtered.style.apply(highlight_row, axis=1), height=400)

    # Download
    st.markdown("---")
    st.subheader("💾 Download Processed File")
    output = BytesIO()
    df_filtered.to_excel(output, index=False)
    output.seek(0)
    st.download_button(
        "⬇️ Download Excel",
        data=output,
        file_name=f"processed_auction_lots_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("👆 Upload an Excel file to get started!")

# Footer
st.markdown("---")
st.markdown("<div style='text-align:center;color:#718096;padding:20px;'>Made with ❤️ by Henrietta Atsenokhai | © 2025</div>", unsafe_allow_html=True)
