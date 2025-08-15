import yfinance as yf
import pandas as pd
import numpy as np
import os
from typing import Dict, Any, List, Optional

from .multibagger_metrics import MultibaggerMetricsFetcher
from .value_metrics import ValueMetricsFetcher
from .deep_value_metrics import DeepValueMetricsFetcher

class UniversalDataFetcher:
    """Fælles datahåndtering for alle investeringsstrategier"""
    
    def __init__(self, cache_dir: str = "./universal_cache"):
        self.cache_dir = cache_dir
        self.multibagger_fetcher = MultibaggerMetricsFetcher()
        self.value_fetcher = ValueMetricsFetcher()
        self.deep_value_fetcher = DeepValueMetricsFetcher()
        
        # Opret cache-mappe hvis den ikke eksisterer
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def fetch_all_metrics(self, ticker: str, strategy_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Henter alle relevante metrikker baseret på strategitype
        Hvis ingen strategitype specificeret, hent alle metrikker
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Tjek om ticker er gyldig
            if not info or 'symbol' not in info or not info['symbol']:
                print(f"Ugyldig ticker: {ticker}")
                return None
                
            metrics = {
                "ticker": ticker,
                "name": info.get("shortName", "N/A"),
                "sector": info.get("sector", "Ukendt"),
                "industry": info.get("industry", "Ukendt"),
                "country": info.get("country", "Ukendt"),
                "market_cap": info.get("marketCap", 0),
                "current_price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                "avg_volume": info.get("averageVolume", 0),
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange", "N/A")
            }
            
            # Hent strategispecifikke metrikker
            if strategy_type == "multibagger" or strategy_type is None:
                metrics.update(self.multibagger_fetcher.fetch_metrics(stock))
            
            if strategy_type == "value" or strategy_type is None:
                metrics.update(self.value_fetcher.fetch_metrics(stock))
            
            if strategy_type == "deep_value" or strategy_type is None:
                metrics.update(self.deep_value_fetcher.fetch_metrics(stock))
            
            return metrics
            
        except Exception as e:
            print(f"Fejl ved hentning af data for {ticker}: {str(e)}")
            return None
    
    def fetch_required_metrics(self, ticker: str, required_metrics: List[str]) -> Dict[str, Any]:
        """Henter kun de specifikke metrikker der er nødvendige for en given profil"""
        # Identificer hvilken strategi der kræves baseret på metrikkerne
        strategy_type = self._determine_strategy_from_metrics(required_metrics)
        
        # Hent alle metrikker for den pågældende strategi
        return self.fetch_all_metrics(ticker, strategy_type)
    
    def _determine_strategy_from_metrics(self, metrics: List[str]) -> str:
        """Bestemmer hvilken strategitype der er nødvendig baseret på metrikkerne"""
        multibagger_metrics = [
            "revenue_growth", "eps_growth", "gross_margin", "peg_ratio",
            "price_above_sma50", "rsi", "volume_surge"
        ]
        
        value_metrics = [
            "pe_ratio", "pb_ratio", "ev_ebitda", "dividend_yield",
            "current_ratio", "roe", "positive_eps_years"
        ]
        
        deep_value_metrics = [
            "cash_to_market_cap", "price_to_nca", "price_to_tangible_book",
            "recent_eps_growth", "news_sentiment"
        ]
        
        # Tæl antallet af metrikker for hver strategi
        counts = {
            "multibagger": sum(1 for m in metrics if m in multibagger_metrics),
            "value": sum(1 for m in metrics if m in value_metrics),
            "deep_value": sum(1 for m in metrics if m in deep_value_metrics)
        }
        
        # Returner strategien med flest matchende metrikker
        return max(counts, key=counts.get)
    
    def fetch_financial_statements(self, ticker: str) -> Dict[str, pd.DataFrame]:
        """Henter finansielle regnskaber for dybere analyse"""
        try:
            stock = yf.Ticker(ticker)
            return {
                "income_stmt": stock.income_stmt,
                "balance_sheet": stock.balance_sheet,
                "cashflow": stock.cashflow
            }
        except Exception as e:
            print(f"Fejl ved hentning af regnskaber for {ticker}: {str(e)}")
            return {}
    
    def fetch_technical_data(self, ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """Henter tekniske data for momentum-analyse"""
        try:
            stock = yf.Ticker(ticker)
            return stock.history(period=period, interval=interval)
        except Exception as e:
            print(f"Fejl ved hentning af tekniske data for {ticker}: {str(e)}")
            return pd.DataFrame()