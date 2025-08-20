# Filnavn: app.py

import streamlit as st
import os
import glob
from core.data.csv_processor import process_finviz_csv
# --- 1. TILFØJ DENNE IMPORT ---
from core.favorites_manager import load_favorites

st.set_page_config(
    page_title="Investment Screener Hjem",
    layout="wide"
)

# --- Centraliseret State Initialisering ---
# Kører kun én gang, når appen starter eller sessionen nulstilles.

# Indlæs den store datafil
if 'processed_dataframe' not in st.session_state:
    st.session_state['processed_dataframe'] = None
    
    # Søg efter en eksisterende CSV-fil i rodmappen
    csv_files = glob.glob("*.csv")
    if len(csv_files) == 1:
        csv_file_path = csv_files[0]
        # Viser kun spinner hvis filen rent faktisk behandles
        with st.spinner(f"Behandler {os.path.basename(csv_file_path)}..."):
            st.session_state['processed_dataframe'] = process_finviz_csv(csv_file_path)
    elif len(csv_files) > 1:
        # Sætter en fejlmeddelelse, der vil blive vist i UI'en
        st.session_state['csv_error'] = "🚨 Fejl: Mere end én CSV-fil fundet. Slet venligst de unødvendige."

# --- 2. TILFØJ DENNE BLOK ---
# Indlæs favorit-listen én gang for hele applikationen.
# Dette sikrer, at listen er klar, uanset om data kommer fra en lokal fil eller en upload.
if 'favorites' not in st.session_state:
    st.session_state.favorites = load_favorites()
# -----------------------------

# --- Hoved UI på forsiden ---
st.title("📊 Velkommen til Investment Screener")
st.sidebar.title("Navigation")

# Vis eventuel fejlmeddelelse fra initialiseringen
if 'csv_error' in st.session_state and st.session_state['csv_error']:
    st.error(st.session_state['csv_error'])

# Tjek om data er blevet indlæst (enten ved start eller via upload)
if st.session_state.get('processed_dataframe') is not None:
    st.success(f"✅ {len(st.session_state['processed_dataframe'])} aktier er indlæst og klar til screening.")
    st.info("👈 Vælg en screener fra navigationen i sidepanelet for at begynde.")
else:
    # Viser kun upload-sektionen, hvis der ikke er en fejl
    if 'csv_error' not in st.session_state or not st.session_state['csv_error']:
        st.warning("⚠️ Ingen data er indlæst.")
        st.info("Placer en Finviz CSV-fil i projektmappen, eller upload en herunder for at starte.")
        
        uploaded_file = st.file_uploader("Upload Finviz CSV-fil", type="csv")
        if uploaded_file is not None:
            with st.spinner("Behandler uploadet fil..."):
                st.session_state['processed_dataframe'] = process_finviz_csv(uploaded_file)
                # FJERNET: st.rerun() - Dette forårsagede problemet
                # Streamlit vil automatisk opdatere siden efter session_state ændres