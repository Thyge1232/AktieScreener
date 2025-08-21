# Fil: core/data/csv_processor.py

import pandas as pd
import re
import numpy as np
import streamlit as st # TILFØJET: Nødvendig for @st.cache_data

# --- HJÆLPEFUNKTIONER (UÆNDRET) ---

def parse_market_cap(market_cap_str):
    """Konverterer markeds værdi streng til float i dollars. Håndterer M, B, T og tal uden suffix korrekt."""
    if pd.isna(market_cap_str) or str(market_cap_str).strip() in ['-', '']:
        return None
    market_cap_str = str(market_cap_str).strip().upper().replace('$', '').replace(',', '')
    multipliers = {'M': 1_000_000, 'B': 1_000_000_000, 'T': 1_000_000_000_000}
    suffix = market_cap_str[-1]
    if suffix in multipliers:
        number_part = market_cap_str[:-1]
        try:
            number = float(number_part)
            return number * multipliers[suffix]
        except ValueError:
            return None
    try:
        number = float(market_cap_str)
        return number * 1_000_000
    except ValueError:
        print(f"[DEBUG] Kunne ikke parse market cap for: '{market_cap_str}'")
        return None

def find_column_name(df, possible_names):
    """Finder det første matchende kolonnenavn i en liste."""
    for name in possible_names:
        if name in df.columns:
            return name
    return None


@st.cache_data
def process_finviz_csv(file_or_path, cache_key):
    """
    Indlæser og parser en Finviz CSV-fil.
    'cache_key' bruges til at invalidere cachen, når filen ændres.
    """
    try:
        # --- START PÅ NY KODE ---
        # Tjek om input er en filsti (string) eller et UploadedFile-objekt
        if isinstance(file_or_path, str):
            file_name = file_or_path
        else:
            # Antag det er et UploadedFile-objekt, som har et .name attribut
            file_name = file_or_path.name
        
        # Print navnet på filen, der bliver behandlet.
        # Dette print vil KUN blive vist, når cachen misses.
        print(f"⚙️ [CACHE MISS] Behandler nu filen: {file_name}")
        # --- SLUT PÅ NY KODE ---

        df = pd.read_csv(file_or_path, sep=',', on_bad_lines='skip', header=0, quoting=1)
        df.columns = df.columns.str.strip().str.replace('"', '', regex=False)

        if 'Ticker' in df.columns:
            df = df.dropna(subset=['Ticker'], how='all')

        # --- Databehandling (uændret) ---
        if "Market Cap" in df.columns:
            df["Market Cap"] = df["Market Cap"].apply(parse_market_cap)

        percentage_columns = [col for col in df.columns if '%' in col or 'Yield' in col or 'Ratio' in col or 'Margin' in col or 'Ownership' in col or 'Change' in col or 'Return' in col or 'Performance' in col or 'Growth' in col or 'Transactions' in col or 'Interest' in col]
        for col in percentage_columns:
            if df[col].dtype == 'object':
                df[col] = pd.to_numeric(df[col].astype(str).str.rstrip('%'), errors='coerce') / 100.0

        non_numeric_cols = {"Ticker", "Company", "Sector", "Industry", "Country", "Earnings Date"}
        cols_to_convert = [col for col in df.columns if col not in non_numeric_cols]

        for col in cols_to_convert:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        if 'Country' in df.columns:
            df['Country'] = df['Country'].astype(str).str.strip().str.strip('"')

        try:
            price_col = find_column_name(df, ['Price', 'Last', 'Close'])
            book_per_share_col = find_column_name(df, ['Book/sh', 'Book Value Per Share'])
            if price_col and book_per_share_col:
                df['Price vs. Book/sh'] = np.nan
                valid_mask = (df[book_per_share_col] > 0)
                df.loc[valid_mask, 'Price vs. Book/sh'] = df.loc[valid_mask, price_col] / df.loc[valid_mask, book_per_share_col]
            else:
                df['Price vs. Book/sh'] = np.nan
        except Exception:
            if 'Price vs. Book/sh' not in df.columns:
                df['Price vs. Book/sh'] = np.nan
        
        return df

    except Exception as e:
        print(f"Fejl under behandling af CSV-fil: {e}")
        return pd.DataFrame()