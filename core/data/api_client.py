# core/data/api_client.py
import requests
import pandas as pd
import time
import streamlit as st

API_KEY = st.secrets["ALPHA_VANTAGE_API_KEY"]

# Eksisterende funktioner
@st.cache_data(ttl=600)
def get_fundamental_data(ticker):
    """Henter fundamental data (Company Overview) for en enkelt ticker."""
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={API_KEY}'
    
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        
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
    """Henter og sammensætter fundamental data for favoritter."""
    if not tickers:
        return pd.DataFrame()
    
    all_stock_data = []
    progress_bar = st.progress(0, text="Henter data...")
    
    for i, ticker in enumerate(tickers):
        data = get_fundamental_data(ticker)
        if data:
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
        
        time.sleep(1)
        progress_bar.progress((i + 1) / len(tickers), text=f"Henter data for {ticker}...")
    
    progress_bar.empty()
    return pd.DataFrame(all_stock_data)

# NYE FUNKTIONER TIL BACKTESTING:

@st.cache_data(ttl=3600)
def get_daily_prices(ticker, outputsize="full"):
    """Henter daglige prisdata for backtesting."""
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={ticker}&outputsize={outputsize}&apikey={API_KEY}'
    
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        
        if "Time Series (Daily)" in data:
            df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.astype(float)
            
            # Omdøb kolonner
            df.columns = ['Open', 'High', 'Low', 'Close', 'Adjusted_Close', 'Volume', 'Dividend', 'Split_Coefficient']
            df = df.sort_index()
            df['Ticker'] = ticker
            
            return df
        else:
            st.error(f"Ingen prisdata fundet for {ticker}")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Fejl ved hentning af prisdata for {ticker}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_weekly_prices(ticker):
    """Henter ugentlige prisdata."""
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY_ADJUSTED&symbol={ticker}&apikey={API_KEY}'
    
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        
        if "Weekly Adjusted Time Series" in data:
            df = pd.DataFrame.from_dict(data["Weekly Adjusted Time Series"], orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.astype(float)
            
            df.columns = ['Open', 'High', 'Low', 'Close', 'Adjusted_Close', 'Volume', 'Dividend']
            df = df.sort_index()
            df['Ticker'] = ticker
            
            return df
        else:
            st.error(f"Ingen ugentlige data fundet for {ticker}")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Fejl ved hentning af ugentlige data for {ticker}: {e}")
        return pd.DataFrame()

def get_portfolio_historical_data(tickers, period="daily", max_tickers=5):
    """Henter historiske data for portefølje af aktier."""
    if len(tickers) > max_tickers:
        st.warning(f"Reducerer til de første {max_tickers} aktier for at spare API-kald")
        tickers = tickers[:max_tickers]
    
    all_data = []
    progress_bar = st.progress(0, text="Henter historiske data...")
    
    for i, ticker in enumerate(tickers):
        if period == "daily":
            df = get_daily_prices(ticker, "compact")
        else:
            df = get_weekly_prices(ticker)
            
        if not df.empty:
            all_data.append(df)
        
        # Respekter API-grænser
        time.sleep(10)  # 6 kald pr. minut
        
        progress_bar.progress((i + 1) / len(tickers), text=f"Henter data for {ticker}...")
    
    progress_bar.empty()
    
    if all_data:
        return pd.concat(all_data, ignore_index=False)
    else:
        return pd.DataFrame()