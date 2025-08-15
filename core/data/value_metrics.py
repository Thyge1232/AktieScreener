import pandas as pd
import numpy as np
from typing import Dict, Any

class ValueMetricsFetcher:
    """Henter value-specifikke metrikker"""
    
    def fetch_metrics(self, stock) -> Dict[str, Any]:
        """Henter alle value-specifikke metrikker"""
        info = stock.info
        metrics = {}
        
        # Value-metrikker
        metrics["pe_ratio"] = info.get("trailingPE")
        metrics["pb_ratio"] = info.get("priceToBook")
        metrics["ev_ebitda"] = info.get("enterpriseToEbitda")
        metrics["dividend_yield"] = info.get("dividendYield", 0) * 100
        metrics["debt_to_equity"] = info.get("debtToEquity")
        metrics["current_ratio"] = info.get("currentRatio")
        metrics["roe"] = info.get("returnOnEquity")
        
        # EPS-konsistens
        try:
            income_stmt = stock.income_stmt
            if not income_stmt.empty:
                net_income = income_stmt.loc["Net Income"]
                positive_eps_years = sum(1 for val in net_income if val > 0)
                metrics["positive_eps_years"] = positive_eps_years
        except:
            pass
        
        return metrics