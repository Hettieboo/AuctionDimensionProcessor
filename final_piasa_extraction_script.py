import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
import plotly.express as px

class AuctionDimensionExtractor:
    """Optimized auction dimension extraction with vectorized operations."""
    
    MULTIPLES_MAP = {
        "paire": 2, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
        "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10
    }
    
    DIM_PATTERNS = {
        'H': re.compile(r'H\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
        'L': re.compile(r'L\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
        'P': re.compile(r'P\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
        'Diameter': re.compile(r'Ø\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE)
    }
    
    KEYWORDS_2D = {
        'huile', 'gouache', 'aquarelle', 'acrylique', 'pastel', 'crayon',
        'dessin', 'gravure', 'lithographie', 'sérigraphie', 'estampe',
        'papier', 'toile', 'canvas', 'carton', 'technique mixte',
        'oil', 'watercolor', 'acrylic', 'drawing', 'print', 'painting',
        'encre', 'fusain', 'sanguine', 'collage', 'mixed media'
    }
    
    IGNORE_TERMS = {'provenance', 'bibliographie', 'catalogue', 'album', 'exposition', 'collection'}

    @staticmethod
    def normalize_number(s):
        """Convert string to float, handling European decimal format."""
        try:
            return float(str(s).replace(",", "."))
        except (ValueError, AttributeError):
            return None

    @classmethod
    def detect_multiples(cls, text):
        """Extract item count from text."""
        text_lower = str(text).lower()
        for word, count in cls.MULTIPLES_MAP.items():
            if word in text_lower:
                return count
        m = re.search(r'ensemble\s+de\s+(\d+)', text_lower)
        return int(m.group(1)) if m else 1

    @classmethod
    def detect_item_type(cls, text):
        """Classify as 2D or 3D based on keywords."""
        text_lower = str(text).lower()[:300]
        has_2d_keywords = any(k in text_lower for k in cls.KEYWORDS_2D)
        has_ignore = any(t in text_lower for t in cls.IGNORE_TERMS)
        return '2D' if has_2d_keywords and not has_ignore else '3D'

    @classmethod
    def extract_dimensions(cls, text):
        """Parse dimensions from text segments."""
        dims_list = []
        for segment in re.split(r'[;\n]', str(text)):
            d = {key: None for key in cls.DIM_PATTERNS}
            for key, pattern in cls.DIM_PATTERNS.items():
                m = pattern.search(segment)
                if m:
                    d[key] = cls.normalize_number(m.group(1))
            dims_list.append(d)
        return dims_list

    @classmethod
    def process_dataframe(cls, df, typeset_col='TYPESET'):
        """Process dataframe with optimized row expansion."""
        rows = []
        
        for _, row in df.iterrows():
            text = str(row.get(typeset_col, ''))
            multiples = cls.detect_multiples(text)
            item_type = cls.detect_item_type(text)
            dims_list = cls.extract_dimensions(text)
            
            # Handle dimension replication
            if len(dims_list) == 1 and multiples > 1:
                dims_list = dims_list * multiples
            elif len(dims_list) > 1 and multiples > len(dims_list):
                cycles = (multiples + len(dims_list) - 1) // len(dims_list)
                dims_list = (dims_list * cycles)[:multiples]
            
            # Expand rows
            for dims in dims_list:
                new_row = row.to_dict()
                new_row.update(dims)
                new_row['ITEM_TYPE'] = item_type
                new_row['ITEM_COUNT'] = multiples
                new_row['D'] = dims.get('Diameter') or dims.get('P') or dims.get('L')
                rows.append(new_row)
        
        return pd.DataFrame(rows)


def prepare_shipping(df):
    """Apply shipping conversion rules."""
    df = df.copy()
    logs = []
    
    for idx, row in df.iterrows():
        log = []
        
        if row['ITEM_TYPE'] == '2D':
            max_dim = max(pd.to_numeric(row['H'], errors='coerce') or 0,
                         pd.to_numeric(row['L'], errors='coerce') or 0)
            df.at[idx, 'L'] = max_dim
            df.at[idx, 'D'] = 5
            log.append("2D: L=max(H,L), D=5")
        else:
            if pd.notna(row.get('Diameter')):
                if row['L'] != row['Diameter']:
                    df.at[idx, 'L'] = row['Diameter']
                    log.append("L=Ø")
                if row['D'] != row['Diameter']:
                    df.at[idx, 'D'] = row['Diameter']
                    log.append("D=Ø")
        
        logs.append("; ".join(log))
    
    df['CONVERSION_LOG'] = logs
    return df


# ============================================================================
# STREAMLIT UI
# ============================================================================

st.set_page_config(page_title="Auction Dimension Processor", layout="wide", page_icon="📦")

# Custom styling
st.markdown("""
<style>
    .stApp {background: linear-gradient(135deg, #f9f9f9, #e0f7fa);}
    .main-header {
        text-align: center;
        font-size: 42px;
        font-weight: bold;
        background: linear-gradient(135deg, #ff6f61, #1abc9c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
    }
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📦 Auction Dimension Processor</div>', unsafe_allow_html=True)
st.markdown("### Transform auction data with precision and style")
st.markdown("---")

# Sidebar configuration
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/000000/auction.png", width=100)
    st.markdown("## 📊 Features")
    st.info("""
    • Upload Excel auction data
    • Extract H, L, P, Diameter
    • Detect 2D/3D items & multiples
    • Prepare shipping-ready D values
    • Visualize metrics & download
    """)
    
    typeset_col = st.text_input("TypeSet Column Name", value="TYPESET")
    show_shipping = st.checkbox("Apply Shipping Rules", value=True)
    st.markdown("---")
    st.markdown("**Made with ❤️**")

# File upload
uploaded_file = st.file_uploader("📂 Upload Excel file", type=["xlsx"])

if uploaded_file:
    # Load data
    df = pd.read_excel(uploaded_file)
    st.success(f"✅ Loaded {len(df):,} rows")
    
    with st.expander("🔍 View Original Data"):
        st.dataframe(df.head(10), use_container_width=True)
    
    # Process data
    with st.spinner("Processing auction data..."):
        extractor = AuctionDimensionExtractor()
        df_processed = extractor.process_dataframe(df, typeset_col)
        df_final = prepare_shipping(df_processed) if show_shipping else df_processed
    
    # Key metrics
    st.markdown("---")
    st.subheader("📊 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    total_items = len(df_final)
    total_2d = (df_final['ITEM_TYPE'] == '2D').sum()
    total_3d = (df_final['ITEM_TYPE'] == '3D').sum()
    total_converted = (df_final['CONVERSION_LOG'] != '').sum()
    
    col1.metric("Total Items", f"{total_items:,}")
    col2.metric("2D Items", f"{total_2d:,}", f"{total_2d/total_items*100:.1f}%")
    col3.metric("3D Items", f"{total_3d:,}", f"{total_3d/total_items*100:.1f}%")
    col4.metric("Converted Rows", f"{total_converted:,}")
    
    # Filters
    st.markdown("---")
    st.subheader("⚡ Filters")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        type_filter = st.multiselect(
            "Filter by Item Type",
            options=['2D', '3D'],
            default=['2D', '3D']
        )
    with col2:
        conversion_filter = st.checkbox("Show only converted rows")
    
    df_filtered = df_final[df_final['ITEM_TYPE'].isin(type_filter)].copy()
    if conversion_filter:
        df_filtered = df_filtered[df_filtered['CONVERSION_LOG'] != '']
    
    st.info(f"📋 Showing {len(df_filtered):,} of {len(df_final):,} rows")
    
    # Visualizations
    st.markdown("---")
    st.subheader("📈 Visualizations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        type_counts = df_filtered['ITEM_TYPE'].value_counts()
        fig = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title="Item Type Distribution",
            color=type_counts.index,
            color_discrete_map={'2D': '#FF6F61', '3D': '#1ABC9C'}
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        df_plot = df_filtered[df_filtered['D'].notna()].copy()
        fig2 = px.histogram(
            df_plot,
            x='D',
            color='ITEM_TYPE',
            nbins=30,
            title="Distribution of D by Item Type",
            color_discrete_map={'2D': '#FF6F61', '3D': '#1ABC9C'},
            barmode='overlay',
            opacity=0.7
        )
        fig2.update_layout(bargap=0.1)
        st.plotly_chart(fig2, use_container_width=True)
    
    # Data table
    st.markdown("---")
    st.subheader("🔍 Processed Data")
    
    def highlight_row(row):
        """Apply row coloring based on item type."""
        color = '#FFEBE6' if row['ITEM_TYPE'] == '2D' else '#E0F7FA'
        return [f'background-color: {color}'] * len(row)
    
    display_cols = [col for col in df_filtered.columns if col in 
                   ['ITEM_TYPE', 'H', 'L', 'P', 'Diameter', 'D', 'ITEM_COUNT', 'CONVERSION_LOG']]
    
    st.dataframe(
        df_filtered[display_cols].style.apply(highlight_row, axis=1),
        height=400,
        use_container_width=True
    )
    
    # Download section
    st.markdown("---")
    st.subheader("💾 Download Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        output = BytesIO()
        df_filtered.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"processed_auction_{timestamp}.xlsx"
        
        st.download_button(
            label="⬇️ Download Excel",
            data=output,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col2:
        csv_output = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_output,
            file_name=f"processed_auction_{timestamp}.csv",
            mime="text/csv"
        )

else:
    st.info("👆 Upload an Excel file to begin processing")
    st.markdown("""
    ### How it works:
    1. **Upload** your auction Excel file
    2. **Extract** dimensions (H, L, P, Ø) automatically
    3. **Classify** items as 2D or 3D
    4. **Apply** shipping rules for logistics
    5. **Download** processed results
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#718096;padding:20px;'>"
    "Made with ❤️ by Henrietta Atsenokhai | © 2025"
    "</div>",
    unsafe_allow_html=True
)
