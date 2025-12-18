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

st.set_page_config(
    page_title="Auction Dimension Processor",
    layout="wide",
    page_icon="🎨",
    initial_sidebar_state="expanded"
)

# Enhanced custom styling
st.markdown("""
<style>
    /* Main app background with elegant gradient */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Main content area */
    .main .block-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }
    
    /* Beautiful header */
    .main-header {
        text-align: center;
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
    }
    
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    /* Metric cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 8px 16px rgba(102, 126, 234, 0.4);
        border: none;
    }
    
    div[data-testid="metric-container"] label {
        color: white !important;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: white !important;
        font-size: 2rem;
        font-weight: 700;
    }
    
    div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
        color: rgba(255,255,255,0.8) !important;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: white !important;
    }
    
    /* Buttons */
    .stDownloadButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stDownloadButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Info boxes */
    .stAlert {
        border-radius: 10px;
        border-left: 5px solid #667eea;
    }
    
    /* Upload area */
    .uploadedFile {
        border-radius: 10px;
        border: 2px dashed #667eea;
    }
    
    /* Dividers */
    hr {
        margin: 2rem 0;
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
    }
</style>
""", unsafe_allow_html=True)

# Header with beautiful emoji
st.markdown('<div class="main-header">🎨 Auction Dimension Processor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Transform auction data with precision and elegance</div>', unsafe_allow_html=True)
st.markdown("---")

# Beautiful sidebar with custom logo
with st.sidebar:
    # Custom SVG logo
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <svg width="120" height="120" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
            <!-- Auction hammer -->
            <defs>
                <linearGradient id="hammerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#f093fb;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#f5576c;stop-opacity:1" />
                </linearGradient>
                <linearGradient id="blockGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#ffd89b;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#19547b;stop-opacity:1" />
                </linearGradient>
            </defs>
            
            <!-- Auction block -->
            <rect x="40" y="140" width="80" height="40" rx="5" fill="url(#blockGrad)" />
            
            <!-- Hammer handle -->
            <rect x="85" y="40" width="15" height="100" rx="7" fill="url(#hammerGrad)" 
                  transform="rotate(-25 92 90)" />
            
            <!-- Hammer head -->
            <rect x="65" y="25" width="50" height="25" rx="5" fill="url(#hammerGrad)" 
                  transform="rotate(-25 90 37)" />
            
            <!-- Sparkles -->
            <circle cx="160" cy="40" r="3" fill="#fff" opacity="0.8">
                <animate attributeName="opacity" values="0.8;0.3;0.8" dur="2s" repeatCount="indefinite"/>
            </circle>
            <circle cx="170" cy="60" r="2" fill="#fff" opacity="0.6">
                <animate attributeName="opacity" values="0.6;0.2;0.6" dur="1.5s" repeatCount="indefinite"/>
            </circle>
            <circle cx="155" cy="70" r="2.5" fill="#fff" opacity="0.7">
                <animate attributeName="opacity" values="0.7;0.3;0.7" dur="1.8s" repeatCount="indefinite"/>
            </circle>
        </svg>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("## 📊 Features")
    st.markdown("""
    <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; backdrop-filter: blur(10px);">
    ✨ <b>Smart Extraction</b><br/>
    📐 Auto-detect dimensions<br/>
    🎭 Classify 2D/3D items<br/>
    📦 Shipping-ready output<br/>
    📊 Beautiful analytics<br/>
    💾 Multi-format export
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("## ⚙️ Settings")
    typeset_col = st.text_input("TypeSet Column", value="TYPESET")
    show_shipping = st.checkbox("Apply Shipping Rules", value=True)
    
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <p style="font-size: 0.9rem; opacity: 0.8;">Made with ❤️</p>
        <p style="font-size: 1.1rem; font-weight: 600;">Henrietta Atsenokhai</p>
    </div>
    """, unsafe_allow_html=True)

# File upload with enhanced styling
uploaded_file = st.file_uploader(
    "📂 Upload your Excel file",
    type=["xlsx"],
    help="Select an Excel file containing auction lot data"
)

if uploaded_file:
    # Load data
    df = pd.read_excel(uploaded_file)
    st.success(f"✅ Successfully loaded {len(df):,} rows")
    
    with st.expander("🔍 View Original Data", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)
    
    # Process data
    with st.spinner("🔄 Processing auction data..."):
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
    col4.metric("Converted", f"{total_converted:,}")
    
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
            color_discrete_map={'2D': '#f093fb', '3D': '#667eea'}
        )
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            textfont_size=14
        )
        fig.update_layout(
            showlegend=True,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        df_plot = df_filtered[df_filtered['D'].notna()].copy()
        fig2 = px.histogram(
            df_plot,
            x='D',
            color='ITEM_TYPE',
            nbins=30,
            title="Distribution of D by Item Type",
            color_discrete_map={'2D': '#f093fb', '3D': '#667eea'},
            barmode='overlay',
            opacity=0.7
        )
        fig2.update_layout(
            bargap=0.1,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12)
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Data table
    st.markdown("---")
    st.subheader("🔍 Processed Data")
    
    def highlight_row(row):
        """Apply row coloring based on item type."""
        color = '#FFF0F5' if row['ITEM_TYPE'] == '2D' else '#F0F4FF'
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
            label="📥 Download Excel",
            data=output,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col2:
        csv_output = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv_output,
            file_name=f"processed_auction_{timestamp}.csv",
            mime="text/csv"
        )

else:
    # Beautiful empty state
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px;">
        <div style="font-size: 80px; margin-bottom: 20px;">📤</div>
        <h2 style="color: #667eea; margin-bottom: 10px;">Ready to Process Your Auction Data</h2>
        <p style="color: #666; font-size: 1.1rem; margin-bottom: 30px;">
            Upload an Excel file to begin the transformation
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1)); 
                    padding: 30px; border-radius: 15px; border: 2px dashed #667eea;">
            <h3 style="color: #667eea; margin-bottom: 20px;">📋 How it works:</h3>
            <ol style="color: #666; line-height: 2; font-size: 1rem;">
                <li><b>Upload</b> your auction Excel file</li>
                <li><b>Extract</b> dimensions automatically (H, L, P, Ø)</li>
                <li><b>Classify</b> items as 2D or 3D</li>
                <li><b>Apply</b> shipping rules for logistics</li>
                <li><b>Download</b> processed results</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align:center; padding: 30px 0;'>
        <p style='color: #667eea; font-size: 1.1rem; margin-bottom: 10px;'>
            Built with precision and passion
        </p>
        <p style='color: #999; font-size: 0.9rem;'>
            © 2025 Henrietta Atsenokhai. All rights reserved.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
