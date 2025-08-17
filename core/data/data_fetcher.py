# core/data/data_fetcher.py

import requests
import os
import time
from io import StringIO
import csv
from diskcache import Cache
from dotenv import load_dotenv # Indlæs dotenv for at parse .env filen

# Indlæs variabler fra .env filen
load_dotenv()

# Opret cache-mappe
cache = Cache('.cache_av')

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"

def fetch_stock_data_av(ticker):
    # Tjek først i cachen
    cached = cache.get(ticker)
    if cached is not None:
        print(f"Cache hit for {ticker}")
        return cached

    print(f"Henter data for {ticker}...")

    # ---- 1. Hent OVERVIEW (fundamentale data) ----
    overview_params = {
        "function": "OVERVIEW",
        "symbol": ticker,
        "apikey": API_KEY
    }

    try:
        response = requests.get(BASE_URL, params=overview_params)
        response.raise_for_status()
        overview_data = response.json()

        overview_data = response.json()

        # --- FEJLFINDING: Print hele API-svaret ---
        print(f"Rå data fra OVERVIEW API for {ticker}:")
        print(overview_data) 
        # --- SLUT FEJLFINDING ---


        if not overview_data or "Note" in overview_data:
            print(f"Advarsel: Ingen data for {ticker}")
            time.sleep(12)
            return None

        # ---- 2. Behandle fundamentale data ----
        processed_data = {
            "MarketCap": float(overview_data.get("MarketCapitalization", 0)),
            "PERatio": float(overview_data.get("PERatio", 0)),
            "EPS": float(overview_data.get("EPS", 0)),
            "Sector": overview_data.get("Sector", "N/A"),
            "Industry": overview_data.get("Industry", "N/A"),
        }

        # ---- 3. Hent tekniske indikatorer ----
        tech_data = fetch_technical_indicators(ticker)
        processed_data.update(tech_data)

        # ---- 4. Gem i cache i 1 time ----
        cache.set(ticker, processed_data, expire=3600)
        time.sleep(12)  # Rate limit
        return processed_data

    except Exception as e:
        print(f"Fejl ved hentning af data for {ticker}: {e}")
        return None


def fetch_technical_indicators(ticker):
    """Hent tekniske indikatorer som SMA og RSI"""
    tech_data = {}

    # Simple Moving Average (20 days)
    sma_params = {
        "function": "SMA",
        "symbol": ticker,
        "interval": "daily",
        "time_period": 20,
        "series_type": "close",
        "apikey": API_KEY
    }
    try:
        response = requests.get(BASE_URL, params=sma_params)
        data = response.json().get("Technical Analysis: SMA", {})
        if data:
            latest_sma = float(list(data.values())[0]["SMA"])
            tech_data["SMA_20"] = latest_sma
    except Exception as e:
        print(f"Fejl ved hentning af SMA for {ticker}: {e}")

    # Relative Strength Index (14 days)
    rsi_params = {
        "function": "RSI",
        "symbol": ticker,
        "interval": "daily",
        "time_period": 14,
        "series_type": "close",
        "apikey": API_KEY
    }
    try:
        response = requests.get(BASE_URL, params=rsi_params)
        data = response.json().get("Technical Analysis: RSI", {})
        if data:
            latest_rsi = float(list(data.values())[0]["RSI"])
            tech_data["RSI_14"] = latest_rsi
    except Exception as e:
        print(f"Fejl ved hentning af RSI for {ticker}: {e}")

    return tech_data


def get_all_listed_stocks():
    """Hent liste over alle aktier fra NASDAQ og NYSE"""
    params = {
        "function": "LISTING_STATUS",
        "apikey": API_KEY
    }
    response = requests.get(BASE_URL, params=params)
    csv_data = StringIO(response.text)
    reader = csv.DictReader(csv_data)
    return [
        row["symbol"] for row in reader
        if row["exchange"] in ["NASDAQ", "NYSE"] and row["assetType"] == "Stock"
    ]