import streamlit as st
import os
import glob
from core.data.csv_processor import process_finviz_csv

# Grundlæggende sidekonfiguration
st.set_page_config(
    page_title="Investment Screener",
    layout="wide"
)

# --- Centraliseret CSV-indlæsning ---
# Kører kun én gang, når appen starter, eller hvis data endnu ikke er indlæst.
if 'processed_dataframe' not in st.session_state:
    st.session_state['processed_dataframe'] = None  # Initialiser
    
    csv_files_in_root = glob.glob("*.csv")
    
    if len(csv_files_in_root) == 1:
        csv_file_path = csv_files_in_root[0]
        # Vis en statusmeddelelse, mens filen behandles
        with st.spinner(f"Indlæser og behandler {os.path.basename(csv_file_path)}..."):
            st.session_state['processed_dataframe'] = process_finviz_csv(csv_file_path)
    elif len(csv_files_in_root) > 1:
        st.error(f"🚨 Fejl: Flere CSV-filer fundet. Slet venligst de unødvendige og behold kun én i projektmappen.")
    else:
        st.info("ℹ️ Ingen CSV-fil fundet. Placer venligst en Finviz CSV-fil i projektmappen for at starte.")

# Streamlit håndterer navigationen automatisk baseret på 'pages' mappen.
# Denne fil kan forblive simpel. Hovedindholdet vises på de enkelte sider.
st.sidebar.title("Investment Screener")
st.sidebar.info(
    """
    Vælg en screener fra navigationen ovenfor.
    Data indlæses automatisk fra den CSV-fil, der er placeret i projektmappen.
    """
)