import pandas as pd
import re
import numpy as np

def parse_market_cap(market_cap_str):
    """Konverterer markeds værdi streng til float i dollars."""
    if pd.isna(market_cap_str) or market_cap_str in ['-', '']:
        return None
    
    market_cap_str = str(market_cap_str).strip().replace('$', '').replace(' ', '')
    market_cap_str = market_cap_str.replace(',', '')
    
    multipliers = {'M': 1_000_000, 'B': 1_000_000_000, 'T': 1_000_000_000_000}
    match = re.search(r'^([0-9]+\.?[0-9]*)\s*([MBT])$', market_cap_str, re.IGNORECASE)
    
    if match:
        number_part = match.group(1)
        try:
            number = float(number_part)
            suffix = match.group(2).upper()
            return number * multipliers[suffix]
        except (ValueError, KeyError):
            pass

    try:
        number = float(market_cap_str)
        return number * 1_000_000
    except ValueError:
        print(f"[DEBUG] Kunne ikke parse market cap for: '{market_cap_str}'")
        return None

def parse_percentage(percent_str):
    """Konverterer procent streng (f.eks. '25.00%') til float (0.25)."""
    if pd.isna(percent_str) or percent_str in ['-', '']:
        return None
    percent_str = str(percent_str).strip().rstrip('%')
    try:
        return float(percent_str) / 100.0
    except ValueError:
        return None

def parse_numeric(value_str):
    """Konverterer en generel streng til float, håndterer '-'."""
    if pd.isna(value_str) or value_str in ['-', '']:
        return None
    try:
        value_str_clean = str(value_str).strip().replace(',', '')
        return float(value_str_clean)
    except ValueError:
        return None

def process_finviz_csv(file):
    """Indlæser og parser en Finviz CSV-fil."""
    try:
        df = pd.read_csv(file, sep=',', on_bad_lines='skip', header=0, quoting=1)
        df.columns = df.columns.str.strip().str.replace('"', '')
        
        if 'Ticker' in df.columns:
            df = df.dropna(subset=['Ticker'], how='all')
        else:
            df = df.dropna(how='all')

        percentage_columns = [
            "EPS Growth Past 3 Years", "EPS Growth Past 5 Years", "EPS Growth Next 5 Years",
            "Sales Growth Past 3 Years", "Sales Growth Past 5 Years", "Sales Growth Quarter Over Quarter",
            "Return on Assets", "Return on Equity", "Return on Invested Capital",
            "Gross Margin", "Operating Margin", "Profit Margin",
            "Performance (Month)", "Performance (Quarter)", "Performance (Year)",
            "Performance (3 Years)", "Performance (5 Years)",
            "Insider Ownership", "Change"
        ]

        for col in percentage_columns:
            if col in df.columns:
                df[col] = df[col].apply(parse_percentage)

        if "Market Cap" in df.columns:
            df["Market Cap"] = df["Market Cap"].apply(parse_market_cap)

        non_parsing_columns = set(percentage_columns) | {"No.", "Ticker", "Company", "Sector", "Industry", "Country", "Earnings Date", "Market Cap"}
        numeric_columns_to_process = set(df.columns) - non_parsing_columns
        
        for col in numeric_columns_to_process:
            if col in df.columns:
                df[col] = df[col].apply(parse_numeric)

        if 'Country' in df.columns:
            df['Country'] = df['Country'].str.strip().str.strip('"')

        # ========================================================================
        # == RETTET KODEBLOK STARTER HER ==
        # Beregn den nye 'Price vs. Book/sh' kolonne til Asset Value profilen.
        try:
            # Tjekker efter de korrekte kolonnenavne fra din CSV-fil
            if 'Price' in df.columns and 'Book/sh' in df.columns:
                
                # Betingelse for kun at beregne på gyldige, positive tal
                valid_book_values = (df['Book/sh'].notna()) & (df['Book/sh'] > 0)
                
                # Opret den nye kolonne og initialiser med NaN
                df['Price vs. Book/sh'] = np.nan
                
                # Udfør beregningen og indsæt i den nye kolonne
                df.loc[valid_book_values, 'Price vs. Book/sh'] = df['Price'] / df['Book/sh']
                
                print("Successfully calculated 'Price vs. Book/sh' column.")
            else:
                # Opdateret advarsel med det korrekte kolonnenavn
                print("Advarsel: 'Price' eller 'Book/sh' kolonner mangler. Kan ikke beregne 'Price vs. Book/sh'.")

        except Exception as e:
            print(f"En fejl opstod under beregning af 'Price vs. Book/sh': {e}")
        # ========================================================================

        return df

    except Exception as e:
        print(f"Fejl under behandling af CSV-fil: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()