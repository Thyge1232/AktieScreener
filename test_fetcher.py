# test_fetcher.py

# --- Konfiguration ---
# Sørg for, at din .env fil er oprettet og indeholder din API-nøgle
# Sørg for, at .env filen ikke er i git (tilføj til .gitignore)

import os
import sys

# --- Tilføj 'core' mappen til Python path, så vi kan importere fra den ---
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))

# --- Importer funktionen ---
from core.data.data_fetcher import fetch_stock_data_av

def main():
    ticker = "IBM" # Du kan ændre denne til en anden ticker du vil teste
    print(f"Starter test for {ticker}...")
    
    # --- Kald funktionen ---
    data = fetch_stock_data_av(ticker)
    
    # --- Print resultatet ---
    if data:
        print(f"\n--- Data for {ticker} ---")
        for key, value in data.items():
            print(f"{key}: {value}")
    else:
        print(f"\nIngen data blev returneret for {ticker}. Tjek loggen ovenfor for fejl.")

if __name__ == "__main__":
    main()