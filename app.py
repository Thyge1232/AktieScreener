# app.py
import streamlit as st
import os
import glob
from core.data.csv_processor import process_finviz_csv

st.set_page_config(
    page_title="Investment Screener Hjem",
    layout="wide"
)

# --- Centraliseret CSV-indlæsning ---
# Kører kun én gang, når appen starter.
if 'processed_dataframe' not in st.session_state:
    st.session_state['processed_dataframe'] = None
    
    # Søg efter en enkelt CSV-fil i rodmappen
    csv_files = glob.glob("*.csv")
    
    if len(csv_files) == 1:
        csv_file_path = csv_files[0]
        with st.spinner(f"Behandler {os.path.basename(csv_file_path)}..."):
            st.session_state['processed_dataframe'] = process_finviz_csv(csv_file_path)
    elif len(csv_files) > 1:
        st.error("🚨 Fejl: Mere end én CSV-fil fundet. Slet venligst de unødvendige og behold kun den ene.")
    # Hvis ingen fil findes, venter vi på upload.

# --- Hoved UI på forsiden ---
st.title("📊 Velkommen til Investment Screener")
st.sidebar.title("Navigation")

if st.session_state.get('processed_dataframe') is not None:
    st.success(f"✅ {len(st.session_state['processed_dataframe'])} aktier er indlæst og klar til screening.")
    st.info("👈 Vælg en screener fra navigationen i sidepanelet for at begynde.")
else:
    st.warning("⚠️ Ingen data er indlæst.")
    st.info("Placer en Finviz CSV-fil i projektmappen, eller upload en herunder for at starte.")
    
    uploaded_file = st.file_uploader("Upload Finviz CSV-fil", type="csv")
    if uploaded_file is not None:
        with st.spinner("Behandler uploadet fil..."):
            st.session_state['processed_dataframe'] = process_finviz_csv(uploaded_file)
            st.rerun() # Genindlæs siden for at opdatere status