# auction_processor_app.py
import streamlit as st
import pandas as pd
import re
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ----------------- AuctionDimensionProcessor -----------------
class AuctionDimensionProcessor:
    def __init__(self):
        # Map words to numbers
        self.multiples_keywords = {
            "paire": 2, "deux": 2, "trois": 3, "quatre": 4,
            "cinq": 5, "six": 6, "sept": 7, "huit": 8,
            "neuf": 9, "dix": 10
        }
        # Patterns for dimensions
        self.dimension_patterns = {
            'H': re.compile(r'H\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'L': re.compile(r'L\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'P': re.compile(r'P\s*[:\s]*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
        }
        
        # Track metrics
        self.metrics = {
            'total_items': 0,
            'processed_items': 0,
            'errors': 0,
            'item_types': {},
            'processing_time': 0
        }
    
    def normalize_number(self, num_str):
        if not num_str:
            return None
        try:
            return float(num_str.replace(',', '.'))
        except:
            return None
    
    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        start_time = datetime.now()
        self.metrics['total_items'] = len(df)
        
        df['ITEM_COUNT'] = 1
        df['ITEM_TYPE'] = '3D'
        
        # Track item types
        for item_type in df['ITEM_TYPE'].unique():
            self.metrics['item_types'][item_type] = (df['ITEM_TYPE'] == item_type).sum()
        
        self.metrics['processed_items'] = len(df)
        self.metrics['processing_time'] = (datetime.now() - start_time).total_seconds()
        
        return df
    
    def get_metrics(self):
        return self.metrics

# ----------------- Streamlit Interface -----------------
st.set_page_config(
    page_title="Auction Dimension Processor",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 10px 0;
    }
    .big-font {
        font-size: 50px !important;
        font-weight: bold;
        color: #667eea;
    }
    .medium-font {
        font-size: 24px !important;
        color: #4a5568;
    }
    h1 {
        color: #2d3748;
        font-weight: 800;
        text-align: center;
        padding: 20px 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
    }
    .upload-section {
        background: white;
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        margin: 20px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("📦 Auction Dimension Processor")
st.markdown("### *Transform your auction data with precision and elegance*")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/000000/auction.png", width=100)
    st.markdown("## 📊 About")
    st.info("""
    **Auction Dimension Processor** helps you:
    - 📤 Upload auction data (Excel)
    - 🔄 Process dimensions automatically
    - 📈 View real-time metrics
    - 💾 Download processed results
    """)
    
    st.markdown("---")
    st.markdown("### 🎯 Quick Stats")
    if 'processor' in st.session_state and st.session_state.get('processed', False):
        metrics = st.session_state.processor.get_metrics()
        st.metric("Total Items", metrics['total_items'])
        st.metric("Processing Time", f"{metrics['processing_time']:.2f}s")
        st.metric("Success Rate", f"{(metrics['processed_items']/metrics['total_items']*100):.1f}%")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.markdown("#### 📁 Upload Your File")
    uploaded_file = st.file_uploader(
        "Choose an Excel file containing auction lots",
        type=["xlsx"],
        help="Upload your Excel file with auction data"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.markdown("#### ℹ️ File Requirements")
    st.markdown("""
    - Format: `.xlsx`
    - Contains auction lot data
    - Dimension information
    """)
    st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        
        # Display success message
        st.balloons()
        st.success(f"✅ Successfully loaded **{len(df):,}** rows!")
        
        # Initialize processor
        processor = AuctionDimensionProcessor()
        st.session_state.processor = processor
        
        # Processing
        with st.spinner("🔄 Processing your auction lots..."):
            df_final = processor.process_dataframe(df)
            st.session_state.processed = True
        
        st.success("✨ Processing complete!")
        
        # Key Metrics Section
        st.markdown("---")
        st.markdown("## 📊 Key Metrics Dashboard")
        
        metrics = processor.get_metrics()
        
        # Top metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric(
                label="📦 Total Items",
                value=f"{metrics['total_items']:,}",
                delta="Processed"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric(
                label="⚡ Processing Time",
                value=f"{metrics['processing_time']:.2f}s",
                delta=f"{metrics['total_items']/metrics['processing_time']:.0f} items/s" if metrics['processing_time'] > 0 else "N/A"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            success_rate = (metrics['processed_items'] / metrics['total_items'] * 100) if metrics['total_items'] > 0 else 0
            st.metric(
                label="✅ Success Rate",
                value=f"{success_rate:.1f}%",
                delta="Excellent" if success_rate > 95 else "Good"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric(
                label="📋 Columns",
                value=len(df_final.columns),
                delta=f"{len(df_final.columns) - len(df)} new"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Charts row
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            # Item types distribution
            if metrics['item_types']:
                fig = px.pie(
                    values=list(metrics['item_types'].values()),
                    names=list(metrics['item_types'].keys()),
                    title="📊 Item Type Distribution",
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Processing summary
            summary_data = {
                'Category': ['Total Items', 'Processed', 'Errors'],
                'Count': [metrics['total_items'], metrics['processed_items'], metrics['errors']]
            }
            fig = go.Figure(data=[
                go.Bar(
                    x=summary_data['Category'],
                    y=summary_data['Count'],
                    marker_color=['#667eea', '#28a745', '#dc3545'],
                    text=summary_data['Count'],
                    textposition='auto',
                )
            ])
            fig.update_layout(
                title="📈 Processing Summary",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                yaxis_title="Count",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Data preview
        st.markdown("---")
        st.markdown("## 🔍 Data Preview")
        
        # Show column statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"**Rows:** {len(df_final):,}")
        with col2:
            st.info(f"**Columns:** {len(df_final.columns)}")
        with col3:
            memory_usage = df_final.memory_usage(deep=True).sum() / 1024**2
            st.info(f"**Memory:** {memory_usage:.2f} MB")
        
        # Interactive data table
        st.dataframe(
            df_final.head(20),
            use_container_width=True,
            height=400
        )
        
        # Column information
        with st.expander("📋 View Column Information"):
            col_info = pd.DataFrame({
                'Column': df_final.columns,
                'Type': df_final.dtypes.values,
                'Non-Null Count': df_final.count().values,
                'Null Count': df_final.isnull().sum().values
            })
            st.dataframe(col_info, use_container_width=True)
        
        # Download section
        st.markdown("---")
        st.markdown("## 💾 Download Results")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            output = BytesIO()
            df_final.to_excel(output, index=False)
            output.seek(0)
            
            st.download_button(
                label="⬇️ Download Processed Excel File",
                data=output,
                file_name=f"processed_auction_lots_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.exception(e)
else:
    # Welcome screen when no file is uploaded
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("👆 **Get started by uploading an Excel file above**")
        
        # Feature highlights
        st.markdown("### ✨ Features")
        features = [
            "🚀 Fast processing of large datasets",
            "📊 Real-time metrics and visualizations",
            "🎯 Automatic dimension extraction",
            "💾 Easy Excel export",
            "📈 Comprehensive data insights"
        ]
        for feature in features:
            st.markdown(f"- {feature}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #718096; padding: 20px;'>
        <p>Made with ❤️ using Streamlit | © 2024 Auction Dimension Processor</p>
    </div>
    """,
    unsafe_allow_html=True
)
