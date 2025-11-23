# app.py
import streamlit as st
import pandas as pd
from auction_processor import AuctionDimensionProcessor  # Ensure this file has your working class

# Page configuration
st.set_page_config(
    page_title="Auction Dimension Extractor",
    page_icon="📦",  # Shipping box icon
    layout="centered",
)

st.title("📦 Auction Dimension Extractor")
st.write("Upload an Excel file containing a 'Description' column to extract dimensions automatically.")

# File uploader
uploaded_file = st.file_uploader("Choose your Excel file", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # Load file
        df = pd.read_excel(uploaded_file)
        st.success("File loaded successfully! Preview below:")
        st.dataframe(df.head())

        # Process dataframe
        processor = AuctionDimensionProcessor()
        df_processed = processor.process_dataframe(df)

        st.write("✅ Extracted Dimensions:")
        st.dataframe(df_processed)

        # Download button
        output_file = "extracted_dimensions.xlsx"
        df_processed.to_excel(output_file, index=False)
        st.download_button(
            label="Download extracted dimensions",
            data=open(output_file, "rb").read(),
            file_name=output_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Error processing file: {e}")
else:
    st.info("Please upload a file to get started.")
