# Filnavn: app.py

import streamlit as st
import os
import glob
from core.data.csv_processor import process_finviz_csv
from core.favorites_manager import load_favorites

st.set_page_config(
    page_title="Investment Screener Hjem",
    layout="wide"
)

# --- Centraliseret State Initialisering ---

if 'processed_dataframe' not in st.session_state:
    st.session_state['processed_dataframe'] = None
    # --- ÆNDRING 1: Initialiser en ny session state variabel til filnavnet ---
    st.session_state['loaded_csv_filename'] = None
    
    csv_files = glob.glob("*.csv")
    if len(csv_files) == 1:
        csv_file_path = csv_files[0]
        mod_time = os.path.getmtime(csv_file_path)
        
        with st.spinner(f"Behandler {os.path.basename(csv_file_path)}..."):
            st.session_state['processed_dataframe'] = process_finviz_csv(csv_file_path, mod_time)
            # Gem navnet på den indlæste fil
            st.session_state['loaded_csv_filename'] = os.path.basename(csv_file_path)
            
    elif len(csv_files) > 1:
        st.session_state['csv_error'] = "🚨 Fejl: Mere end én CSV-fil fundet. Slet venligst de unødvendige."

# Indlæs favorit-listen én gang for hele applikationen.
if 'favorites' not in st.session_state:
    st.session_state.favorites = load_favorites()

# Initialiser andre session state variabler
if 'force_favorites_update' not in st.session_state:
    st.session_state.force_favorites_update = False
if 'force_rerender_count' not in st.session_state:
    st.session_state.force_rerender_count = 0

# --- Navigation & Sidebar ---
st.sidebar.title("📊 Navigation")

st.sidebar.markdown("---")
st.sidebar.subheader("Cache Kontrol")

if st.sidebar.button("Ryd Data Cache"):
    st.cache_data.clear()
    st.toast("Data cache er blevet ryddet!", icon="✅")
    st.rerun()

nav_options = ["🏠 Hjem", "📈 Value Screener", "🚀 Multibagger Finder", "⭐ Mine Favoritter", "🔄 Backtesting"]
selected_page = st.sidebar.selectbox("Vælg side:", nav_options, index=0)

st.sidebar.markdown("---")
if st.session_state.get('processed_dataframe') is not None:
    df = st.session_state['processed_dataframe']
    st.sidebar.success(f"✅ {len(df)} aktier indlæst")
    
    # --- ÆNDRING 2: Vis filnavnet i sidebaren ---
    filename = st.session_state.get('loaded_csv_filename')
    if filename:
        st.sidebar.caption(f"Kilde: {filename}")

if st.session_state.favorites:
    st.sidebar.info(f"⭐ {len(st.session_state.favorites)} favoritter")


# --- Page Routing ---
if selected_page == "🏠 Hjem":
    st.title("📊 Velkommen til Investment Screener")
    
    if 'csv_error' in st.session_state and st.session_state['csv_error']:
        st.error(st.session_state['csv_error'])
    
    if st.session_state.get('processed_dataframe') is not None:
        df = st.session_state['processed_dataframe']
        
        # --- ÆNDRING 3: Vis filnavnet i success-beskeden på forsiden ---
        filename = st.session_state.get('loaded_csv_filename', 'Filen') # Brug et default for en pæn besked
        st.success(f"✅ **{filename}** ({len(df)} aktier) er indlæst og klar til screening.")
        
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Totale Aktier", len(df))
        with col2: st.metric("Favoritter", len(st.session_state.favorites))
        with col3: st.metric("Sektorer", df['Sector'].nunique())
        
        st.info("👈 Vælg en screener fra navigationen i sidepanelet for at begynde.")
    else:
        if 'csv_error' not in st.session_state or not st.session_state['csv_error']:
            st.warning("⚠️ Ingen data er indlæst.")
            st.info("Placer en Finviz CSV-fil i projektmappen, eller upload en herunder for at starte.")
            
            uploaded_file = st.file_uploader("Upload Finviz CSV-fil", type="csv")
            if uploaded_file is not None:
                with st.spinner("Behandler uploadet fil..."):
                    cache_key = (uploaded_file.name, uploaded_file.size)
                    st.session_state['processed_dataframe'] = process_finviz_csv(uploaded_file, cache_key)
                    # Gem også navnet på den uploadede fil
                    st.session_state['loaded_csv_filename'] = uploaded_file.name
                    st.rerun()


elif selected_page == "📈 Value Screener":
    # Check if file exists before executing
    if os.path.exists('pages/value_screener.py'):
        exec(open('pages/value_screener.py', encoding='utf-8').read())
    else:
        st.error("📁 Value Screener ikke fundet: `pages/value_screener.py`")

elif selected_page == "🚀 Multibagger Finder":
    if os.path.exists('pages/multibagger_screener.py'):
        exec(open('pages/multibagger_screener.py', encoding='utf-8').read())
    else:
        st.error("📁 Multibagger Screener ikke fundet: `pages/multibagger_screener.py`")
        st.info("Opret denne fil baseret på value_screener.py med vækst-kriterier.")

elif selected_page == "⭐ Mine Favoritter":
    if os.path.exists('pages/favorites.py'):
        exec(open('pages/favorites.py', encoding='utf-8').read())
    else:
        st.error("📁 Favoritter-siden ikke fundet: `pages/favorites.py`")

elif selected_page == "🔄 Backtesting":
    # Validate API key first
    try:
        api_key = st.secrets.get("ALPHA_VANTAGE_API_KEY")
        if not api_key:
            st.error("🔑 Alpha Vantage API-nøgle mangler i secrets.toml")
            st.code('ALPHA_VANTAGE_API_KEY = "din_api_noegle_her"')
        else:
            # Check if backtesting files exist
            if os.path.exists('pages/backtesting.py'):
                if os.path.exists('core/backtesting/strategy_engine.py'):
                    exec(open('pages/backtesting.py', encoding='utf-8').read())
                else:
                    st.error("📁 Strategy engine ikke fundet: `core/backtesting/strategy_engine.py`")
            else:
                st.error("📁 Backtesting-siden ikke fundet: `pages/backtesting.py`")
    except Exception as e:
        st.error(f"🔑 API konfigurationsfejl: {e}")

# Footer info
st.sidebar.markdown("---")
st.sidebar.markdown("**💡 Workflow:**")
st.sidebar.markdown("1. Kør screenere")  
st.sidebar.markdown("2. Gem favoritter")
st.sidebar.markdown("3. Test strategier")