# core/data/api_client.py
import requests
import pandas as pd
import time
import streamlit as st

# INDSÆT DIN EGEN GRATIS API-NØGLE HER
API_KEY = st.secrets["ALPHA_VANTAGE_API_KEY"]

# Brug Streamlits cache til at undgå at kalde for den samme ticker flere gange hurtigt efter hinanden
@st.cache_data(ttl=600) # Cache i 10 minutter
def get_fundamental_data(ticker):
    """Henter fundamental data (Company Overview) for en enkelt ticker."""
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={API_KEY}'
    try:
        r = requests.get(url)
        r.raise_for_status()  # Stopper hvis der er en HTTP-fejl
        data = r.json()
        
        # Alpha Vantage returnerer en tom dict {} hvis tickeren ikke findes
        if data and "Symbol" in data:
            return data
        else:
            st.warning(f"Kunne ikke finde data for '{ticker}'. Tjek om tickeren er korrekt.")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Netværksfejl under hentning af data for {ticker}: {e}")
        return None
    except Exception as e:
        st.error(f"En ukendt fejl opstod for {ticker}: {e}")
        return None

def get_data_for_favorites(tickers: list):
    """
    Henter og sammensætter fundamental data for en liste af favorit-tickers.
    Viser en progress bar i Streamlit.
    """
    if not tickers:
        return pd.DataFrame()

    all_stock_data = []
    
    # Opret en progress bar
    progress_bar = st.progress(0, text="Henter data...")

    for i, ticker in enumerate(tickers):
        data = get_fundamental_data(ticker)
        if data:
            # Flad JSON-svaret ud til en simpel dictionary, der passer til en DataFrame
            stock_info = {
                'Ticker': data.get('Symbol'),
                'Company': data.get('Name'),
                'Sector': data.get('Sector'),
                'P/E': pd.to_numeric(data.get('PERatio'), errors='coerce'),
                'Market Cap': pd.to_numeric(data.get('MarketCapitalization'), errors='coerce'),
                'Dividend Yield': pd.to_numeric(data.get('DividendYield'), errors='coerce') * 100,
                'EPS': pd.to_numeric(data.get('EPS'), errors='coerce')
            }
            all_stock_data.append(stock_info)
        
        # VIGTIGT: Respekter API-grænsen. Alpha Vantage har en grænse for kald pr. minut.
        # En lille pause er nødvendig for at undgå at blive blokeret.
        time.sleep(1) # 1 sekunds pause er en sikker start
        
        # Opdater progress bar
        progress_bar.progress((i + 1) / len(tickers), text=f"Henter data for {ticker}...")

    progress_bar.empty() # Fjern progress bar når den er færdig
    return pd.DataFrame(all_stock_data)