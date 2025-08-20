# pages/favorites.py
import streamlit as st
import pandas as pd
from core.favorites_manager import load_favorites, save_favorites
from core.data.api_client import get_data_for_favorites

st.set_page_config(layout="wide")
st.title("⭐ Mine Favoritter")

# Indlæs den gemte liste af ticker-navne
favorite_tickers = load_favorites()

if not favorite_tickers:
    st.info("Du har endnu ikke tilføjet nogen favoritter. Find aktier i en af screenerne og tilføj dem med ➕.")
    st.stop()

# Vis den nuværende liste og giv mulighed for at fjerne aktier
st.subheader("Administrer din liste")
tickers_to_remove = []
for ticker in favorite_tickers:
    col1, col2 = st.columns([10, 1])
    col1.write(ticker)
    if col2.button("🗑️", key=f"del_{ticker}", help=f"Fjern {ticker} fra favoritter"):
        tickers_to_remove.append(ticker)

if tickers_to_remove:
    updated_favorites = [t for t in favorite_tickers if t not in tickers_to_remove]
    save_favorites(updated_favorites)
    st.success(f"Fjernede {', '.join(tickers_to_remove)} fra din liste.")
    # Nulstil data-cachen for at tvinge genhentning af den nye, kortere liste
    if 'favorites_data' in st.session_state:
        del st.session_state['favorites_data']
    st.rerun()

st.markdown("---")
st.subheader("Live Data Opdatering")

# Knappen, der udløser de få, hurtige API-kald
if st.button("Hent Seneste Data for Favoritter"):
    # Kald API'en kun for denne lille liste
    live_data_df = get_data_for_favorites(favorite_tickers)
    
    # Gem de friske data i session_state til visning
    if not live_data_df.empty:
        st.session_state.favorites_data = live_data_df

# Vis de senest hentede data, hvis de findes
if 'favorites_data' in st.session_state:
    st.info("Viser senest hentede data. Klik på knappen ovenfor for at opdatere.")
    
    # Formater data pænt til visning
    df_display = st.session_state.favorites_data.copy()
    
    # Formater Market Cap
    if 'Market Cap' in df_display.columns:
        df_display['Market Cap'] = df_display['Market Cap'].apply(
            lambda x: f"${x/1e9:.2f}B" if pd.notnull(x) and x >= 1e9 else (f"${x/1e6:.1f}M" if pd.notnull(x) else "-")
        )
    # Formater P/E og EPS
    if 'P/E' in df_display.columns:
        df_display['P/E'] = df_display['P/E'].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "-")
    if 'EPS' in df_display.columns:
        df_display['EPS'] = df_display['EPS'].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "-")
    # Formater Dividend Yield
    if 'Dividend Yield' in df_display.columns:
        df_display['Dividend Yield'] = df_display['Dividend Yield'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "-")

    st.dataframe(df_display, use_container_width=True)
else:
    st.write("Klik på opdatér-knappen for at hente de seneste priser og nøgletal.")