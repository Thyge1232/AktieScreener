import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

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
        
        # Gældsmetrikker - konverter til decimal hvis nødvendigt
        debt_to_equity = info.get("debtToEquity")
        metrics["debt_to_equity"] = debt_to_equity / 100 if debt_to_equity else None
        metrics["debt_to_ebitda"] = info.get("debtToEbitda")
        metrics["interest_coverage"] = info.get("interestCoverage")
        
        # Værdiansættelse
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
        except Exception:
            metrics["price_above_sma50"] = None
            metrics["rsi"] = None
            metrics["volume_surge"] = None
        
        return metrics
    
    def _fetch_financial_metrics(self, stock: yf.Ticker, info: Dict) -> Dict[str, Any]:
        """Basis finansielle nøgletal"""
        try:
            return {
                "roe": info.get("returnOnEquity"),
                "gross_margin": self._calculate_gross_margin(stock),
                "operating_margin": info.get("operatingMargins"),
                "profit_margin": info.get("profitMargins"),
                "current_ratio": info.get("currentRatio"),
                "quick_ratio": info.get("quickRatio")
            }
        except Exception as e:
            logger.warning(f"Fejl i financial metrics: {e}")
            return {}
    
    def _fetch_growth_metrics(self, stock: yf.Ticker) -> Dict[str, Any]:
        """Vækstmetrikker"""
        try:
            # Hent historiske data
            income_stmt = stock.income_stmt
            if income_stmt.empty:
                return {"revenue_growth": None, "eps_growth": None}
            
            revenue_growth = self._calculate_revenue_growth(income_stmt)
            eps_growth = self._calculate_eps_growth(stock)
            
            return {
                "revenue_growth": revenue_growth,
                "eps_growth": eps_growth,
                "earnings_growth": stock.info.get("earningsGrowth")
            }
        except Exception as e:
            logger.warning(f"Fejl i growth metrics: {e}")
            return {"revenue_growth": None, "eps_growth": None}
    
    def _fetch_debt_metrics(self, info: Dict) -> Dict[str, Any]:
        """Gældsmetrikker"""
        try:
            return {
                "debt_to_equity": info.get("debtToEquity", 0) / 100 if info.get("debtToEquity") else None,
                "debt_to_ebitda": self._calculate_debt_to_ebitda(info),
                "interest_coverage": self._calculate_interest_coverage(info),
                "total_debt": info.get("totalDebt"),
                "total_cash": info.get("totalCash")
            }
        except Exception as e:
            logger.warning(f"Fejl i debt metrics: {e}")
            return {}
    
    def _fetch_valuation_metrics(self, info: Dict) -> Dict[str, Any]:
        """Værdiansættelsesmetrikker"""
        try:
            pe_ratio = info.get("trailingPE")
            peg_ratio = info.get("pegRatio")
            
            return {
                "pe_ratio": pe_ratio,
                "peg_ratio": peg_ratio,
                "pb_ratio": info.get("priceToBook"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "price_to_book": info.get("priceToBook")
            }
        except Exception as e:
            logger.warning(f"Fejl i valuation metrics: {e}")
            return {}
    
    def _fetch_technical_metrics(self, stock: yf.Ticker) -> Dict[str, Any]:
        """Tekniske indikatorer"""
        try:
            # Hent prishistorik
            hist = stock.history(period="6mo", interval="1d")
            if hist.empty:
                return {}
            
            current_price = hist["Close"].iloc[-1]
            sma_50 = hist["Close"].tail(50).mean()
            
            return {
                "price_above_sma50": current_price > sma_50 if not pd.isna(sma_50) else None,
                "rsi": self._calculate_rsi(hist["Close"]),
                "sma_50": sma_50,
                "current_price": current_price,
                "price_change_52w": self._calculate_52w_change(hist)
            }
        except Exception as e:
            logger.warning(f"Fejl i technical metrics: {e}")
            return {}
    
    def _calculate_gross_margin(self, stock: yf.Ticker) -> Optional[float]:
        """Beregn bruttomargen"""
        try:
            income_stmt = stock.income_stmt
            if income_stmt.empty:
                return None
            
            revenue = income_stmt.loc["Total Revenue"].iloc[0] if "Total Revenue" in income_stmt.index else None
            cogs = income_stmt.loc["Cost Of Revenue"].iloc[0] if "Cost Of Revenue" in income_stmt.index else None
            
            if revenue and cogs and revenue != 0:
                return (revenue - cogs) / revenue
            return None
        except Exception as e:
            logger.warning(f"Fejl i gross margin: {e}")
            return None
    
    def _calculate_revenue_growth(self, income_stmt: pd.DataFrame) -> Optional[float]:
        """Beregn omsætningsvækst (CAGR over 3 år)"""
        try:
            if "Total Revenue" not in income_stmt.index or income_stmt.shape[1] < 2:
                return None
            
            revenues = income_stmt.loc["Total Revenue"].dropna()
            if len(revenues) < 2:
                return None
            
            # Få seneste og ældste værdi
            latest = revenues.iloc[0]
            oldest = revenues.iloc[-1]
            years = len(revenues) - 1
            
            if oldest <= 0 or years <= 0:
                return None
            
            # CAGR beregning
            cagr = (latest / oldest) ** (1/years) - 1
            return cagr if not pd.isna(cagr) else None
            
        except Exception as e:
            logger.warning(f"Fejl i revenue growth: {e}")
            return None
    
    def _calculate_eps_growth(self, stock: yf.Ticker) -> Optional[float]:
        """Beregn EPS vækst"""
        try:
            info = stock.info
            eps_forward = info.get("forwardEps")
            eps_trailing = info.get("trailingEps")
            
            if eps_forward and eps_trailing and eps_trailing > 0:
                return (eps_forward / eps_trailing) - 1
            
            # Fallback: brug earnings growth fra info
            earnings_growth = info.get("earningsGrowth")
            return earnings_growth if earnings_growth else None
            
        except Exception as e:
            logger.warning(f"Fejl i EPS growth: {e}")
            return None
    
    def _calculate_debt_to_ebitda(self, info: Dict) -> Optional[float]:
        """Beregn debt-to-EBITDA ratio"""
        try:
            total_debt = info.get("totalDebt")
            ebitda = info.get("ebitda")
            
            if total_debt is not None and ebitda and ebitda > 0:
                return total_debt / ebitda
            return None
        except Exception as e:
            logger.warning(f"Fejl i debt to EBITDA: {e}")
            return None
    
    def _calculate_interest_coverage(self, info: Dict) -> Optional[float]:
        """Beregn rentedækningsgrad"""
        try:
            ebit = info.get("ebitda")  # Approximation
            interest_expense = info.get("interestExpense")
            
            if ebit and interest_expense and interest_expense > 0:
                return ebit / interest_expense
            return None
        except Exception as e:
            logger.warning(f"Fejl i interest coverage: {e}")
            return None
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> Optional[float]:
        """Beregn RSI indikator"""
        try:
            if len(prices) < period + 1:
                return None
            
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None
        except Exception as e:
            logger.warning(f"Fejl i RSI: {e}")
            return None
    
    def _calculate_52w_change(self, hist: pd.DataFrame) -> Optional[float]:
        """Beregn 52-ugers prisændring"""
        try:
            if len(hist) < 200:  # Ikke nok data
                return None
            
            current = hist["Close"].iloc[-1]
            year_ago = hist["Close"].iloc[-252] if len(hist) >= 252 else hist["Close"].iloc[0]
            
            return (current / year_ago) - 1 if year_ago > 0 else None
        except Exception as e:
            logger.warning(f"Fejl i 52w change: {e}")
            return None