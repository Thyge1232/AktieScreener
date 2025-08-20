# core/favorites_manager.py
import os

FAVORITES_FILE = "favorites.txt"

def load_favorites():
    """Indlæser favorit-tickers fra en tekstfil."""
    if not os.path.exists(FAVORITES_FILE):
        return []
    with open(FAVORITES_FILE, 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
    return tickers

def save_favorites(tickers):
    """Gemmer en liste af tickers til tekstfilen, én per linje."""
    with open(FAVORITES_FILE, 'w') as f:
        for ticker in tickers:
            f.write(f"{ticker}\n")