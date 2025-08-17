import pandas as pd
import numpy as np
from typing import Dict, Any
import logging
logger = logging.getLogger(__name__)


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
                    
                    shares_outstanding = info.get("sharesOutstanding", 1)
                    current_price = info.get("currentPrice", 0)
                    if tangible_book_value > 0 and shares_outstanding > 0:
                        tangible_book_per_share = tangible_book_value / shares_outstanding
                        metrics["price_to_tangible_book"] = current_price / tangible_book_per_share
                    else:
                        metrics["price_to_tangible_book"] = None
                else:
                    metrics["cash_to_market_cap"] = None
                    metrics["price_to_nca"] = None
                    metrics["price_to_tangible_book"] = None
        except Exception:
            metrics["cash_to_market_cap"] = None
            metrics["price_to_nca"] = None
            metrics["price_to_tangible_book"] = None
        
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
                    else:
                        metrics["recent_eps_growth"] = None
                else:
                    metrics["recent_eps_growth"] = None
            else:
                metrics["recent_eps_growth"] = None
        except Exception:
            metrics["recent_eps_growth"] = None
        
        # Nyhedssentiment (placeholder)
        metrics["news_sentiment"] = 0.5  # Neutral sentiment
        
        return metrics