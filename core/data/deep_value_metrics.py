import pandas as pd
import numpy as np
from typing import Dict, Any

class DeepValueMetricsFetcher:
    """Henter deep value-specifikke metrikker"""
    
    def fetch_metrics(self, stock) -> Dict[str, Any]:
        """Henter alle deep value-specifikke metrikker"""
        info = stock.info
        metrics = {}
        
        # Value-metrikker
        metrics["pe_ratio"] = info.get("trailingPE")
        metrics["pb_ratio"] = info.get("priceToBook")
        metrics["ev_ebitda"] = info.get("enterpriseToEbitda")
        
        # Cash og aktiver
        try:
            balance_sheet = stock.balance_sheet
            if not balance_sheet.empty:
                # Hent seneste års balance sheet
                latest_bs = balance_sheet.iloc[:, 0]
                
                # Beregn netto omsætningsaktiver = omløbsaktiver - totale gæld
                current_assets = latest_bs.get("Total Current Assets", 0)
                total_liabilities = latest_bs.get("Total Liabilities Net Minority Interest", 0)
                nca = current_assets - total_liabilities
                
                # Hent markedsværdi
                market_cap = info.get("marketCap", 0)
                
                # Beregn cash til markedsværdi
                cash = latest_bs.get("Cash And Cash Equivalents", 0)
                
                # Beregn tangibelt bogføringsværdi
                tangible_assets = latest_bs.get("Total Assets", 0) - latest_bs.get("Goodwill", 0)
                tangible_book_value = tangible_assets - total_liabilities
                
                # Beregn metrikker
                if market_cap > 0:
                    metrics["cash_to_market_cap"] = cash / market_cap
                    metrics["price_to_nca"] = market_cap / nca if nca > 0 else None
                    metrics["price_to_tangible_book"] = info.get("currentPrice", 0) / (tangible_book_value / info.get("sharesOutstanding", 1)) if tangible_book_value > 0 else None
        except Exception as e:
            pass
        
        # EPS-vækst
        try:
            income_stmt = stock.income_stmt
            if not income_stmt.empty and "Net Income" in income_stmt.index:
                net_income = income_stmt.loc["Net Income"]
                if len(net_income) >= 3:
                    start_eps = net_income.iloc[2]
                    end_eps = net_income.iloc[0]
                    if start_eps > 0:
                        metrics["recent_eps_growth"] = (end_eps / start_eps) ** (1/2) - 1
        except:
            pass
        
        # Nyhedssentiment (simuleret - i virkeligheden ville du bruge en API)
        try:
            # Dette er en placeholder - i virkeligheden ville du bruge en nyhedssentiment-API
            metrics["news_sentiment"] = 0.5  # 0 (negativ) til 1 (positiv)
        except:
            pass
        
        return metrics