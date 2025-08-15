import os
import json
from typing import Dict, Any, List
import time
import logging

def setup_logging(log_file: str = "investment_screening.log", level: int = logging.INFO):
    """Opsætter logging for applikationen"""
    logging.basicConfig(
        filename=log_file,
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Også log til konsollen
    console = logging.StreamHandler()
    console.setLevel(level)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

def load_json_file(file_path: str) -> Dict[str, Any]:
    """Loader en JSON-fil"""
    if not os.path.exists(file_path):
        return {}
    
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json_file(data: Dict[str, Any], file_path: str):
    """Gemmer data til en JSON-fil"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """Decorator til at prøve igen ved fejl"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts == max_attempts:
                        raise
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

def format_currency(value: float, currency: str = "USD") -> str:
    """Formaterer et tal som valuta"""
    if currency == "USD":
        return f"${value:,.2f}"
    elif currency == "EUR":
        return f"€{value:,.2f}"
    elif currency == "DKK":
        return f"{value:,.2f} DKK"
    else:
        return f"{value:,.2f} {currency}"

def format_percentage(value: float) -> str:
    """Formaterer et tal som procent"""
    return f"{value:.1%}"

def get_market_for_ticker(ticker: str) -> str:
    """Returnerer markedet for en given ticker"""
    if any(ticker.endswith(ext) for ext in [".AS", ".CO", ".DE", ".PA", ".ST", ".SW", ".HE", ".L", ".N"]):
        return "EU"
    elif any(ticker.endswith(ext) for ext in [".TO", ".V"]):
        return "CA"
    elif any(ticker.endswith(ext) for ext in [".HK"]):
        return "HK"
    else:
        return "US"

def calculate_volume_ratio(volume: float, avg_volume: float) -> float:
    """Beregner volumenforholdet"""
    if avg_volume == 0:
        return 0.0
    return volume / avg_volume

def clean_ticker(ticker: str) -> str:
    """Rens en ticker for ekstra tegn"""
    # Fjern eventuelle ekstra tegn efter punktum
    if '.' in ticker:
        parts = ticker.split('.')
        return f"{parts[0]}.{parts[1][0]}"
    return ticker

def get_industry_from_sector(sector: str) -> List[str]:
    """Returnerer industrier inden for en given sektor"""
    sector_industries = {
        "Technology": ["Software", "Semiconductors", "Hardware", "IT Services"],
        "Healthcare": ["Biotechnology", "Pharmaceuticals", "Healthcare Providers", "Medical Devices"],
        "Financial Services": ["Banks", "Insurance", "Capital Markets", "Financial Data & Services"],
        "Consumer Cyclical": ["Automobiles", "Retail", "Travel & Leisure", "Media & Entertainment"],
        "Communication Services": ["Telecommunications", "Media", "Entertainment"],
        "Industrials": ["Aerospace & Defense", "Industrial Manufacturing", "Construction", "Transportation"],
        "Consumer Defensive": ["Food & Beverage", "Household Products", "Personal Products", "Tobacco"],
        "Energy": ["Oil & Gas", "Energy Equipment & Services", "Renewable Energy"],
        "Utilities": ["Electric Utilities", "Gas Utilities", "Water Utilities", "Renewable Utilities"],
        "Basic Materials": ["Chemicals", "Metals & Mining", "Paper & Forest Products", "Construction Materials"],
        "Real Estate": ["Real Estate Development", "REITs", "Real Estate Services"]
    }
    
    return sector_industries.get(sector, [])

def calculate_z_score(current_value: float, historical_values: List[float]) -> float:
    """Beregner Z-score for en værdi i forhold til historiske værdier"""
    if not historical_values:
        return 0.0
    
    mean = sum(historical_values) / len(historical_values)
    variance = sum((x - mean) ** 2 for x in historical_values) / len(historical_values)
    std_dev = variance ** 0.5
    
    if std_dev == 0:
        return 0.0
    
    return (current_value - mean) / std_dev