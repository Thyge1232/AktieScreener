# core/data/api_client.py
import requests
import pandas as pd
import time
import streamlit as st

API_KEY = st.secrets["ALPHA_VANTAGE_API_KEY"]

@st.cache_data(ttl=600)
def get_live_price(ticker):
    """Henter live pris fra Alpha Vantage eller yfinance."""
    try:
        # Prøv Alpha Vantage først
        url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={API_KEY}'
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        
        if "Global Quote" in data and "05. price" in data["Global Quote"]:
            return float(data["Global Quote"]["05. price"])
    except:
        pass  # Brug fallback
    
    # Fallback til yfinance
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        return stock.info.get("regularMarketPrice", None)
    except:
        return None

@st.cache_data(ttl=600)
def get_valuation_data(tickers: list):
    """Henter nøgletal til værdiansættelse for en liste af tickers."""
    if not tickers:
        return pd.DataFrame()

    valuation_data = []
    progress_bar = st.progress(0, text="Henter værdiansættelsesdata...")

    for i, ticker in enumerate(tickers):
        data = get_fundamental_data(ticker)
        if data:
            valuation_info = {
                'Ticker': data.get('Symbol'),
                'Revenue': pd.to_numeric(data.get('RevenueTTM'), errors='coerce'),
                'EBITDA': pd.to_numeric(data.get('EBITDA'), errors='coerce'),
                'Net Income': pd.to_numeric(data.get('NetIncomeTTM'), errors='coerce'),
                'Operating Cash Flow': pd.to_numeric(data.get('OperatingCashflowTTM'), errors='coerce'),
                'Book Value': pd.to_numeric(data.get('BookValue'), errors='coerce'),
                'Dividend Per Share': pd.to_numeric(data.get('DividendPerShare'), errors='coerce'),
                'Shares Outstanding': pd.to_numeric(data.get('SharesOutstanding'), errors='coerce'),
                'Quarterly Revenue Growth': pd.to_numeric(data.get('QuarterlyRevenueGrowthYOY'), errors='coerce'),
                'Beta': pd.to_numeric(data.get('Beta'), errors='coerce'),
                'Debt to Equity': pd.to_numeric(data.get('DebtToEquity'), errors='coerce'),
                'Interest Coverage': pd.to_numeric(data.get('InterestCoverage'), errors='coerce')
            }
            valuation_data.append(valuation_info)

        # Respekter API grænser
        time.sleep(1)
        progress_bar.progress((i + 1) / len(tickers), text=f"Henter data for {ticker}...")

    progress_bar.empty()
    return pd.DataFrame(valuation_data)


@st.cache_data(ttl=600)
def get_fundamental_data(ticker):
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={API_KEY}'
    
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        
        # Tjek for Alpha Vantage rate limit
        if "Information" in data and "api call frequency" in data["Information"].lower():
            st.error("⚠️ Alpha Vantage rate limit nået! Vent 12 sekunder mellem kald.")
            return None
            
        # Tjek om data er gyldig
        if data and "Symbol" in data:
            return data
        else:
            # Hvis Alpha Vantage ikke returnerer data, brug yfinance som fallback
            try:
                import yfinance as yf
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # Returner en struktureret dict med nøgletal
                return {
                    "Symbol": ticker,
                    "Name": info.get("longName", "N/A"),
                    "Sector": info.get("sector", "N/A"),
                    "PERatio": info.get("trailingPE", None),
                    "MarketCapitalization": info.get("marketCap", None),
                    "DividendYield": info.get("dividendYield", None),
                    "EPS": info.get("epsTrailingTwelveMonths", None),
                    "Beta": info.get("beta", None),
                    "DebtToEquity": info.get("debtToEquity", None),
                    "RevenueTTM": info.get("totalRevenue", None),
                    "NetIncomeTTM": info.get("netIncomeToCommon", None),
                    "OperatingCashflowTTM": info.get("operatingCashFlow", None),
                    "BookValue": info.get("bookValue", None),
                    "DividendPerShare": info.get("dividendPerShare", None),
                    "SharesOutstanding": info.get("sharesOutstanding", None),
                    "QuarterlyRevenueGrowthYOY": info.get("quarterlyRevenueGrowthYOY", None),
                    "InterestCoverage": None,  # Ikke tilgængelig i yfinance
                }
            except Exception as e:
                st.warning(f"❌ Fejl ved fallback til yfinance for {ticker}: {e}")
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
    # ⚠️ RET: Fjern de 2 mellemrum før https i URL
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={ticker}&outputsize={outputsize}&apikey={API_KEY}'
    
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        
        # NY: Tjek for Alpha Vantage fejlmeddelelser
        if "Information" in data and "api call frequency" in data["Information"].lower():
            st.error("⚠️ Alpha Vantage rate limit nået! Vent 12 sekunder mellem kald.")
            return pd.DataFrame()
            
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
        time.sleep(12)  
        
        progress_bar.progress((i + 1) / len(tickers), text=f"Henter data for {ticker}...")
    
    progress_bar.empty()
    
    if all_data:
        return pd.concat(all_data, ignore_index=False)
    else:
        return pd.DataFrame()