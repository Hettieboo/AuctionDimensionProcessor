import streamlit as st
import pandas as pd
from final_piasa_extraction_script import AuctionDimensionProcessor

st.set_page_config(page_title="📦 Piasa Auction Dimension Processor", layout="wide")

st.title("📦 Piasa Auction Dimension Processor")
st.markdown(
    """
Upload an Excel file containing auction lots, extract dimensions, classify item types, and download results.
"""
)

# Sidebar
st.sidebar.header("Upload & Options")
uploaded_file = st.sidebar.file_uploader("Upload Excel file (.xlsx)", type=["xlsx"])
show_logs = st.sidebar.checkbox("Show processing logs", value=True)

def highlight_row(row):
    """Color rows based on item type and manual review"""
    if row['MANUAL_REVIEW_REQUIRED']:
        return ['background-color: #FFCCCC'] * len(row)  # Red for manual review
    elif row['ITEM_TYPE'] == '2D':
        return ['background-color: #CCFFCC'] * len(row)  # Green for 2D
    elif row['ITEM_TYPE'] == '3D':
        return ['background-color: #CCCCFF'] * len(row)  # Blue for 3D
    else:
        return [''] * len(row)

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ Loaded {len(df)} rows!")
        st.dataframe(df.head(5))

        if st.button("Process Lots"):
            processor = AuctionDimensionProcessor()
            with st.spinner("Processing lots... ⏳"):
                df_final = processor.process_dataframe(df)

            st.success("✅ Processing completed!")

            # Tabs
            tab1, tab2, tab3 = st.tabs(["Summary Metrics", "Processed Data", "Logs"])

            # --- Tab 1: Summary Metrics ---
            with tab1:
                st.markdown("### 📊 Processing Summary")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Max Items in a Lot", df_final['ITEM_COUNT'].max())
                col2.metric("2D Lots", (df_final['ITEM_TYPE'] == '2D').sum())
                col3.metric("3D Lots", (df_final['ITEM_TYPE'] == '3D').sum())
                col4.metric("Manual Review Required", df_final['MANUAL_REVIEW_REQUIRED'].sum())

                # Top manual review reasons
                manual_review_count = df_final['MANUAL_REVIEW_REQUIRED'].sum()
                if manual_review_count > 0:
                    st.markdown("#### ⚠ Top Manual Review Flags")
                    manual_df = df_final[df_final['MANUAL_REVIEW_REQUIRED'] == True]
                    st.dataframe(
                        manual_df['PROCESSING_FLAGS']
                        .value_counts()
                        .head(10)
                        .rename_axis("Flag")
                        .reset_index(name="Count")
                    )

            # --- Tab 2: Processed Data ---
            with tab2:
                st.markdown("### 📝 Processed Auction Lots")
                st.dataframe(df_final.style.apply(highlight_row, axis=1))

            # --- Tab 3: Logs ---
            with tab3:
                if show_logs:
                    st.markdown("### ⚡ Conversion Logs")
                    log_cols = ['LOT', 'ITEM_TYPE', 'PROCESSING_FLAGS', 'CONVERSION_LOG']
                    log_cols = [col for col in log_cols if col in df_final.columns]
                    st.dataframe(df_final[log_cols])

            # --- Download button ---
            st.markdown("### 💾 Download Processed File")
            output_file = "extracted_dimensions_one_row_per_lot.xlsx"
            df_final.to_excel(output_file, index=False)
            with open(output_file, "rb") as f:
                st.download_button(
                    label="Download Excel",
                    data=f,
                    file_name=output_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
else:
    st.info("Please upload an Excel file to begin processing.")
