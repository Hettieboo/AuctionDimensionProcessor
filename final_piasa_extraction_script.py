import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
import plotly.express as px

class AuctionDimensionExtractor:
    """Comprehensive auction dimension extraction with proper 2D/3D classification."""
    
    def __init__(self):
        # Material keywords for 2D classification
        self.true_2d_materials = [
            'huile', 'gouache', 'aquarelle', 'acrylique', 'pastel', 'crayon',
            'dessin', 'gravure', 'lithographie', 'sérigraphie', 'estampe',
            'papier', 'toile', 'canvas', 'carton', 'technique mixte',
            'oil', 'watercolor', 'acrylic', 'drawing', 'print', 'painting',
            'encre', 'fusain', 'sanguine', 'collage', 'mixed media',
            'offset', 'monotype', 'cyanotype', 'albumine', 'héliogravure'
        ]
        
        # 3D assemblage keywords
        self.assemblage_keywords = ['assemblage', 'relief', 'construction']
        
        # Ignore terms (not actual items)
        self.ignore_terms = {
            'provenance', 'bibliographie', 'catalogue', 'album', 
            'exposition', 'collection', 'galerie', 'musée'
        }
        
        # Number word mapping
        self.number_words = {
            'deux': 2, 'trois': 3, 'quatre': 4, 'cinq': 5,
            'six': 6, 'sept': 7, 'huit': 8, 'neuf': 9, 'dix': 10,
            'onze': 11, 'douze': 12, 'treize': 13, 'quatorze': 14, 'quinze': 15
        }
        
        # Dimension patterns
        self.dim_patterns = {
            'h': re.compile(r'\bH\s*[:.]?\s*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'l': re.compile(r'\bL\s*[:.]?\s*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'p': re.compile(r'\bP\s*[:.]?\s*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
            'diameter': re.compile(r'[ØΦ]\s*[:.]?\s*(\d+(?:[.,]\d+)?)', re.IGNORECASE)
        }
        
        # Unlabeled dimension pattern (e.g., "45 × 34 cm" or "45x34cm")
        self.unlabeled_pattern = re.compile(
            r'(\d+(?:[.,]\d+)?)\s*[×xX*]\s*(\d+(?:[.,]\d+)?)\s*(?:[×xX*]\s*(\d+(?:[.,]\d+)?))?\s*cm',
            re.IGNORECASE
        )

    def normalize_number(self, s):
        """Convert string to float, handling European decimal format."""
        try:
            return float(str(s).strip().replace(",", "."))
        except (ValueError, AttributeError):
            return None

    def detect_item_count(self, text):
        """Extract item count from text with context awareness."""
        text_lower = text.lower()
        
        # Check for ignore terms first
        if any(term in text_lower for term in self.ignore_terms):
            # Still check for explicit "paire de" or "ensemble de"
            if 'paire de' in text_lower or 'paire d' in text_lower:
                return 2, []
            elif m := re.search(r'ensemble\s+de\s+(\d+)', text_lower):
                return int(m.group(1)), []
        
        flags = []
        
        # Check for "chaque" - requires manual verification
        if 'chaque' in text_lower:
            flags.append('CHAQUE_DETECTED')
        
        # Check for "paire" (pair)
        if 'paire' in text_lower or 'pair' in text_lower:
            if 'rideau' in text_lower or 'curtain' in text_lower:
                flags.append('CURTAIN_PAIR_COUNT')
            return 2, flags
        
        # Check for "ensemble de X"
        if m := re.search(r'ensemble\s+de\s+(\d+)', text_lower):
            count = int(m.group(1))
            if count > 10:
                flags.append('HIGH_COUNT')
            return count, flags
        
        # Check for number words
        for word, count in self.number_words.items():
            if word in text_lower:
                # Avoid false positives in context
                if not any(ignore in text_lower for ignore in ['collection', 'galerie']):
                    if count > 10:
                        flags.append('HIGH_COUNT')
                    return count, flags
        
        return 1, flags

    def classify_item_type(self, text):
        """Classify as 2D or 3D based on materials and keywords."""
        text_lower = text.lower()[:400]  # Check first 400 chars
        
        flags = []
        
        # Check for fashion items (clothing sizes)
        if 'taille' in text_lower and any(size in text_lower for size in ['xs', 's', 'm', 'l', 'xl']):
            flags.append('FASHION_ITEM')
            return 'MANUAL_CHECK', flags
        
        # Check for "à décadrer" (to unframe) - indicates 2D
        if 'décadrer' in text_lower or 'decadrer' in text_lower:
            flags.append('DECADRER_2D')
            return '2D', flags
        
        # Check for 2D materials
        has_2d_material = any(mat in text_lower for mat in self.true_2d_materials)
        
        # Check for assemblage (3D even with 2D materials)
        has_assemblage = any(kw in text_lower for kw in self.assemblage_keywords)
        
        if has_assemblage:
            flags.append('ASSEMBLAGE_3D_MANUAL_CHECK')
            return '3D', flags
        
        # Technique mixte on canvas -> 2D
        if ('technique mixte' in text_lower or 'mixed media' in text_lower) and 'toile' in text_lower:
            flags.append('TECHNIQUE_MIXTE_TOILE_RECLASSIFIED')
            return '2D', flags
        
        # Panel objects -> 3D but note it
        if 'panneau' in text_lower or 'panel' in text_lower:
            if not has_2d_material:
                flags.append('PANEL_OBJECT_3D')
                return '3D', flags
        
        return ('2D', flags) if has_2d_material else ('3D', flags)

    def extract_dimensions(self, text):
        """Extract all dimension sets from text."""
        dimension_sets = []
        
        # Split by common separators (semicolons, newlines)
        segments = re.split(r'[;\n]', text)
        
        for segment in segments:
            dims = {}
            
            # Try labeled dimensions first (H:, L:, P:, Ø:)
            for key, pattern in self.dim_patterns.items():
                if match := pattern.search(segment):
                    dims[key] = self.normalize_number(match.group(1))
            
            # Try unlabeled dimensions (45 × 34 cm)
            if not dims:
                if match := self.unlabeled_pattern.search(segment):
                    dims['h'] = self.normalize_number(match.group(1))
                    dims['l'] = self.normalize_number(match.group(2))
                    if match.group(3):
                        dims['p'] = self.normalize_number(match.group(3))
            
            # Only add if we found at least one dimension
            if dims:
                dimension_sets.append(dims)
        
        return dimension_sets

    def process_lot(self, lot_text):
        """Process a single lot and return structured data."""
        # Detect item count
        item_count, count_flags = self.detect_item_count(lot_text)
        
        # Classify item type
        item_type, type_flags = self.classify_item_type(lot_text)
        
        # Extract dimensions
        dim_sets = self.extract_dimensions(lot_text)
        
        # Combine flags
        all_flags = count_flags + type_flags
        
        # Handle no dimensions found
        if not dim_sets:
            all_flags.append('NO_DIMENSIONS')
            return {
                'item_count': item_count,
                'item_type': item_type,
                'dimensions': [],
                'flags': all_flags,
                'conversion_log': 'No dimensions found in text',
                'manual_review': True
            }
        
        # Handle multiple dimension sets for single item
        if len(dim_sets) > 1 and item_count == 1:
            all_flags.append('MULTIPLE_DIMENSIONS_SINGLE_ITEM')
            # Keep largest dimensions
            largest = max(dim_sets, key=lambda d: sum(d.values()))
            dim_sets = [largest]
        
        # Replicate dimensions if needed
        if len(dim_sets) == 1 and item_count > 1:
            dim_sets = dim_sets * item_count
        elif len(dim_sets) < item_count:
            # Cycle through available dimensions
            while len(dim_sets) < item_count:
                dim_sets.append(dim_sets[len(dim_sets) % len(dim_sets)])
        elif len(dim_sets) > item_count:
            dim_sets = dim_sets[:item_count]
        
        # Apply conversion rules
        converted_dims, conversion_log = self.apply_shipping_rules(
            dim_sets, item_type, all_flags
        )
        
        # Determine if manual review needed
        manual_review = bool(all_flags) or item_type == 'MANUAL_CHECK'
        
        return {
            'item_count': item_count,
            'item_type': item_type,
            'dimensions': converted_dims,
            'flags': all_flags,
            'conversion_log': conversion_log,
            'manual_review': manual_review
        }

    def apply_shipping_rules(self, dim_sets, item_type, flags):
        """Apply shipping conversion rules to dimensions."""
        converted = []
        logs = []
        
        for idx, dims in enumerate(dim_sets, 1):
            item_log = []
            converted_dims = dims.copy()
            
            # For 2D items
            if item_type == '2D':
                h = dims.get('h', 0) or 0
                l = dims.get('l', 0) or 0
                
                # L = max(H, L)
                max_dim = max(h, l)
                if max_dim > 0:
                    converted_dims['l'] = max_dim
                    item_log.append(f"Item {idx}: L=max(H,L)")
                
                # D = 5 (standard 2D depth)
                converted_dims['d'] = 5.0
                item_log.append(f"Item {idx}: D=5 (2D)")
            
            # For 3D items
            else:
                # If diameter exists, use it for L and D
                if 'diameter' in dims and dims['diameter']:
                    converted_dims['l'] = dims['diameter']
                    converted_dims['d'] = dims['diameter']
                    item_log.append(f"Item {idx}: L=Ø, D=Ø")
                
                # If P exists, use it for D
                elif 'p' in dims and dims['p']:
                    converted_dims['d'] = dims['p']
                    item_log.append(f"Item {idx}: D=P")
                
                # If only H and L exist, assume D = L
                elif 'h' in dims and 'l' in dims and 'd' not in dims:
                    converted_dims['d'] = dims['l']
                    item_log.append(f"Item {idx}: D=L (assumed)")
                    flags.append('HEIGHT_ONLY_OBJECT')
            
            converted.append(converted_dims)
            logs.append("; ".join(item_log))
        
        return converted, " | ".join(logs)

    def process_dataframe(self, df, typeset_col='TYPESET'):
        """Process entire dataframe."""
        results = []
        
        for idx, row in df.iterrows():
            lot_text = str(row.get(typeset_col, ''))
            
            # Process lot
            lot_data = self.process_lot(lot_text)
            
            # Create rows for each item
            for item_idx, dims in enumerate(lot_data['dimensions'], 1):
                result_row = row.to_dict()
                
                # Add extracted data
                result_row['ITEM_COUNT'] = lot_data['item_count']
                result_row['ITEM_TYPE'] = lot_data['item_type']
                result_row['ITEM_NUMBER'] = item_idx
                
                # Add dimensions with item suffix
                result_row['H'] = dims.get('h')
                result_row['L'] = dims.get('l')
                result_row['D'] = dims.get('d')
                result_row['P'] = dims.get('p')
                result_row['Diameter'] = dims.get('diameter')
                
                # Add metadata
                result_row['MANUAL_REVIEW_REQUIRED'] = lot_data['manual_review']
                result_row['PROCESSING_FLAGS'] = '; '.join(lot_data['flags'])
                result_row['CONVERSION_LOG'] = lot_data['conversion_log']
                
                results.append(result_row)
            
            # If no dimensions, still add a row
            if not lot_data['dimensions']:
                result_row = row.to_dict()
                result_row['ITEM_COUNT'] = lot_data['item_count']
                result_row['ITEM_TYPE'] = lot_data['item_type']
                result_row['ITEM_NUMBER'] = 1
                result_row['H'] = None
                result_row['L'] = None
                result_row['D'] = None
                result_row['P'] = None
                result_row['Diameter'] = None
                result_row['MANUAL_REVIEW_REQUIRED'] = lot_data['manual_review']
                result_row['PROCESSING_FLAGS'] = '; '.join(lot_data['flags'])
                result_row['CONVERSION_LOG'] = lot_data['conversion_log']
                results.append(result_row)
        
        return pd.DataFrame(results)


# ============================================================================
# STREAMLIT UI
# ============================================================================

st.set_page_config(
    page_title="Auction Dimension Processor",
    layout="wide",
    page_icon="📦"
)

st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
    }
    h1 {
        color: #2c3e50;
        font-weight: 600;
    }
    h2, h3 {
        color: #34495e;
    }
    .demo-banner {
        background-color: #f4b942;
        color: #000000;
        padding: 12px;
        text-align: center;
        font-weight: 500;
        font-size: 14px;
        margin-bottom: 0;
    }
    .header-frame {
        background: linear-gradient(135deg, #2d5016 0%, #1a3409 100%);
        padding: 40px 20px;
        border-radius: 8px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .header-frame h1 {
        color: #ffffff;
        margin: 0;
        font-size: 2.5rem;
    }
    .header-frame p {
        color: #d4e7c5;
        margin: 10px 0 0 0;
        font-size: 1.1rem;
    }
</style>
""", unsafe_allow_html=True)

# Top demo banner
st.markdown("""
<div class="demo-banner">
    ⚠️ DEMO VERSION - For demonstration purposes only
</div>
""", unsafe_allow_html=True)

# Header with frame
st.markdown("""
<div class="header-frame">
    <h1>📦 Auction Dimension Processor</h1>
    <p>Extract, classify, and standardize auction lot dimensions for shipping</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    typeset_col = st.text_input("TypeSet Column Name", value="TYPESET")
    
    st.divider()
    
    st.markdown("**📋 Processing Options**")
    show_manual_only = st.checkbox("Show only items requiring manual review", value=False)
    
    st.divider()
    
    st.markdown("**ℹ️ About**")
    st.caption("Extract H, L, P, and Ø dimensions from auction descriptions. Automatically classify items as 2D (artworks) or 3D (objects) and apply shipping rules.")
    
    st.divider()
    
    with st.expander("📖 Help & Documentation"):
        st.markdown("""
        **Required Columns:**
        - `LOT` - Lot identifier
        - `TYPESET` - Full lot description
        
        **Output Columns:**
        - `H`, `L`, `D` - Shipping dimensions
        - `ITEM_TYPE` - 2D/3D/MANUAL_CHECK
        - `MANUAL_REVIEW_REQUIRED` - Boolean
        - `PROCESSING_FLAGS` - Warnings
        - `CONVERSION_LOG` - Processing steps
        """)

# File upload
uploaded_file = st.file_uploader("📁 Upload Excel file (.xlsx)", type=["xlsx"])

if uploaded_file:
    # Load data
    try:
        df = pd.read_excel(uploaded_file)
        
        # Check for required columns
        if typeset_col not in df.columns:
            st.error(f"❌ Column '{typeset_col}' not found in file. Please check column name.")
            st.stop()
        
        st.success(f"✅ Loaded {len(df):,} lots")
        
        with st.expander("👀 View original data"):
            st.dataframe(df.head(10), use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Error loading file: {str(e)}")
        st.stop()
    
    # Process data
    with st.spinner("⚙️ Processing lots..."):
        extractor = AuctionDimensionExtractor()
        df_processed = extractor.process_dataframe(df, typeset_col)
    
    # Apply filters
    df_display = df_processed.copy()
    if show_manual_only:
        df_display = df_display[df_display['MANUAL_REVIEW_REQUIRED'] == True]
    
    # Metrics
    st.divider()
    st.subheader("📊 Processing Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_items = len(df_processed)
    total_2d = (df_processed['ITEM_TYPE'] == '2D').sum()
    total_3d = (df_processed['ITEM_TYPE'] == '3D').sum()
    manual_review = df_processed['MANUAL_REVIEW_REQUIRED'].sum()
    
    col1.metric("Total Items", f"{total_items:,}")
    col2.metric("2D Items", f"{total_2d:,}", f"{total_2d/total_items*100:.1f}%")
    col3.metric("3D Items", f"{total_3d:,}", f"{total_3d/total_items*100:.1f}%")
    col4.metric("Manual Review", f"{manual_review:,}", f"{manual_review/total_items*100:.1f}%")
    
    # Flag summary
    st.subheader("⚠️ Processing Flags")
    
    flags_list = []
    for flags in df_processed['PROCESSING_FLAGS']:
        if flags:
            flags_list.extend([f.strip() for f in str(flags).split(';')])
    
    if flags_list:
        flag_counts = pd.Series(flags_list).value_counts()
        
        col1, col2 = st.columns([2, 1])
        with col1:
            fig_flags = px.bar(
                x=flag_counts.values[:10],
                y=flag_counts.index[:10],
                orientation='h',
                title="Top 10 Processing Flags",
                labels={'x': 'Count', 'y': 'Flag'}
            )
            fig_flags.update_layout(height=400)
            st.plotly_chart(fig_flags, use_container_width=True)
        
        with col2:
            st.markdown("**Flag Descriptions:**")
            st.caption("🔴 **CHAQUE_DETECTED** - Contains 'each', verify count")
            st.caption("🔴 **MULTIPLE_DIMENSIONS** - Multiple sizes found")
            st.caption("🔴 **NO_DIMENSIONS** - No measurements found")
            st.caption("🔴 **HIGH_COUNT** - More than 10 items")
            st.caption("🟡 **FASHION_ITEM** - Clothing size detected")
    else:
        st.info("No processing flags generated - all items processed cleanly!")
    
    # Visualizations
    st.divider()
    st.subheader("📈 Data Visualizations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        type_counts = df_processed['ITEM_TYPE'].value_counts()
        fig = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title="Item Type Distribution",
            color_discrete_map={'2D': '#3498db', '3D': '#e74c3c', 'MANUAL_CHECK': '#f39c12'}
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        df_plot = df_processed[df_processed['D'].notna()].copy()
        if len(df_plot) > 0:
            fig2 = px.histogram(
                df_plot,
                x='D',
                color='ITEM_TYPE',
                nbins=30,
                title="Depth (D) Distribution by Type",
                color_discrete_map={'2D': '#3498db', '3D': '#e74c3c', 'MANUAL_CHECK': '#f39c12'},
                barmode='overlay',
                opacity=0.7
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No depth data to display")
    
    # Data table
    st.divider()
    st.subheader("📋 Processed Data")
    
    # Column selector
    available_cols = df_display.columns.tolist()
    default_cols = [col for col in ['ITEM_TYPE', 'ITEM_COUNT', 'H', 'L', 'D', 'P', 'Diameter', 
                                      'MANUAL_REVIEW_REQUIRED', 'PROCESSING_FLAGS', 'CONVERSION_LOG'] 
                    if col in available_cols]
    
    selected_cols = st.multiselect(
        "Select columns to display",
        options=available_cols,
        default=default_cols
    )
    
    if selected_cols:
        st.caption(f"Showing {len(df_display):,} of {len(df_processed):,} items")
        st.dataframe(df_display[selected_cols], height=400, use_container_width=True)
    
    # Download
    st.divider()
    st.subheader("💾 Download Processed Data")
    
    col1, col2 = st.columns(2)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with col1:
        output = BytesIO()
        df_processed.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        st.download_button(
            label="📥 Download Excel (Full Dataset)",
            data=output,
            file_name=f"auction_dimensions_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col2:
        csv_output = df_processed.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV (Full Dataset)",
            data=csv_output,
            file_name=f"auction_dimensions_{timestamp}.csv",
            mime="text/csv"
        )

else:
    st.info("👆 Upload an Excel file to begin processing")
    
    st.markdown("### ✨ Features")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Dimension Extraction:**
        - H, L, P, and Ø (diameter)
        - Labeled and unlabeled formats
        - Multiple dimension sets
        """)
        
    with col2:
        st.markdown("""
        **Smart Classification:**
        - Automatic 2D/3D detection
        - Material-based analysis
        - Item count detection
        """)
    
    st.markdown("""
    **Shipping Rules:**
    - 2D items: L = max(H,L), D = 5cm
    - 3D items: Complete H×L×D
    - Diameter handling for cylindrical objects
    """)

# Bottom demo banner
st.markdown("""
<div class="demo-banner" style="margin-top: 40px;">
    ⚠️ DEMO VERSION - For demonstration purposes only
</div>
""", unsafe_allow_html=True)
