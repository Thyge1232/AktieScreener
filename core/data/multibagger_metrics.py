import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Any

class MultibaggerMetricsFetcher:
    """Henter multibagger-specifikke metrikker"""
    
    def fetch_metrics(self, stock) -> Dict[str, Any]:
        """Henter alle multibagger-specifikke metrikker"""
        info = stock.info
        metrics = {}
        
        # Fundamentale vækstmetrikker
        metrics["revenue_growth"] = info.get("revenueGrowth")
        metrics["eps_growth"] = info.get("earningsQuarterlyGrowth")
        metrics["gross_margin"] = info.get("grossMargins")
        metrics["debt_to_equity"] = info.get("debtToEquity")
        metrics["debt_to_ebitda"] = info.get("debtToEbitda")
        metrics["interest_coverage"] = info.get("interestCoverage")
        metrics["peg_ratio"] = info.get("pegRatio")
        metrics["roe"] = info.get("returnOnEquity")
        
        # Tekniske metrikker
        try:
            hist = stock.history(period="6mo", interval="1d")
            if len(hist) > 50:
                hist['SMA50'] = hist['Close'].rolling(50).mean()
                hist['RSI'] = ta.rsi(hist['Close'], length=14)
                hist['Volume_SMA'] = hist['Volume'].rolling(20).mean()
                latest = hist.iloc[-1]
                
                metrics["price_above_sma50"] = latest['Close'] > latest['SMA50']
                metrics["rsi"] = latest['RSI']
                metrics["volume_surge"] = latest['Volume'] / latest['Volume_SMA']
        except Exception as e:
            pass
        
        return metrics