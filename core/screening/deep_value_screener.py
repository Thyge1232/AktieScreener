from typing import Dict, List, Any

class DeepValueScreener:
    """Deep value-specifik screening logik"""
    
    def __init__(self, data_fetcher):
        self.data_fetcher = data_fetcher
    
    def screen(self, tickers: List[str], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Screening med en specifik deep value-profil"""
        results = []
        params = profile["parameters"]
        
        for ticker in tickers:
            metrics = self.data_fetcher.fetch_all_metrics(ticker, "deep_value")
            if not metrics:
                continue
                
            if self._passes_filters(metrics, params):
                # Beregn deep value-score
                metrics["deep_value_score"] = self._calculate_score(metrics, profile)
                results.append(metrics)
        
        # Sorter efter deep value-score
        results.sort(key=lambda x: x["deep_value_score"], reverse=True)
        return results
    
    def _passes_filters(self, metrics: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Tjekker om aktien opfylder deep value-profilens kriterier"""
        # Markedsværdi
        market_cap = metrics.get("market_cap", 0)
        if not (params["min_market_cap"] <= market_cap <= params["max_market_cap"]):
            return False
        
        # PE Ratio
        pe_ratio = metrics.get("pe_ratio")
        if pe_ratio and pe_ratio > params["max_pe_ratio"]:
            return False
        
        # PB Ratio
        pb_ratio = metrics.get("pb_ratio")
        if pb_ratio and pb_ratio > params["max_pb_ratio"]:
            return False
        
        # EV/EBITDA
        ev_ebitda = metrics.get("ev_ebitda")
        if ev_ebitda and ev_ebitda > params["max_ev_ebitda"]:
            return False
        
        # Cash til markedsværdi
        cash_to_market_cap = metrics.get("cash_to_market_cap")
        if "min_cash_to_market_cap" in params and cash_to_market_cap and cash_to_market_cap < params["min_cash_to_market_cap"]:
            return False
        
        # Gældskriterier
        debt_to_equity = metrics.get("debt_to_equity")
        if debt_to_equity and debt_to_equity > params["max_debt_to_equity"]:
            return False
            
        interest_coverage = metrics.get("interest_coverage")
        if interest_coverage and interest_coverage < params.get("min_interest_coverage", 0):
            return False
        
        # Netto omsætningsaktiver
        price_to_nca = metrics.get("price_to_nca")
        if "max_price_to_nca" in params and price_to_nca and price_to_nca > params["max_price_to_nca"]:
            return False
        
        # Tangibelt bogføringsforhold
        price_to_tangible_book = metrics.get("price_to_tangible_book")
        if "min_price_to_tangible_book" in params and price_to_tangible_book and price_to_tangible_book < params["min_price_to_tangible_book"]:
            return False
        
        # EPS-vækst (for special situations)
        recent_eps_growth = metrics.get("recent_eps_growth")
        if "min_recent_eps_growth" in params and recent_eps_growth is not None:
            if recent_eps_growth < params["min_recent_eps_growth"]:
                return False
        if "max_recent_eps_growth" in params and recent_eps_growth is not None:
            if recent_eps_growth > params["max_recent_eps_growth"]:
                return False
            
        return True
    
    def _calculate_score(self, metrics: Dict[str, Any], profile: Dict[str, Any]) -> float:
        """Beregner en samlet deep value-score"""
        params = profile["parameters"]
        weights = {
            "pb_ratio": 0.30,
            "cash_value": 0.25,
            "financial_health": 0.25,
            "turnaround_potential": 0.20
        }
        
        score = 0
        
        # PB Ratio score (lavere er bedre)
        if metrics["pb_ratio"] and params["max_pb_ratio"]:
            pb_score = min(1.0, (params["max_pb_ratio"] / metrics["pb_ratio"]))
            score += pb_score * weights["pb_ratio"]
        
        # Cash- og aktivværdi score
        cash_value_score = 0
        if "min_cash_to_market_cap" in params and metrics.get("cash_to_market_cap"):
            cash_score = min(1.0, metrics["cash_to_market_cap"] / params["min_cash_to_market_cap"])
            cash_value_score += cash_score * 0.5
        
        if "min_price_to_tangible_book" in params and metrics.get("price_to_tangible_book"):
            tangible_book_score = min(1.0, params["min_price_to_tangible_book"] / metrics["price_to_tangible_book"])
            cash_value_score += tangible_book_score * 0.5
        
        score += cash_value_score * weights["cash_value"]
        
        # Finansiel sundhedsscore
        health_score = 1.0
        if metrics["debt_to_equity"] and params["max_debt_to_equity"]:
            health_score *= max(0, 1 - (metrics["debt_to_equity"] / params["max_debt_to_equity"]))
        if metrics["interest_coverage"] and "min_interest_coverage" in params:
            health_score *= min(1.0, (metrics["interest_coverage"] / params["min_interest_coverage"]))
        
        score += health_score * weights["financial_health"]
        
        # Turnaround-potentiale (for special situations)
        turnaround_score = 0
        recent_eps_growth = metrics.get("recent_eps_growth")
        if recent_eps_growth is not None:
            # Hvis EPS-vækst er positiv, er det et godt tegn
            turnaround_score = max(0, min(1.0, (recent_eps_growth + 0.2) / 0.4))
        
        # Nyhedssentiment kan også bidrage
        news_sentiment = metrics.get("news_sentiment")
        if news_sentiment is not None:
            turnaround_score = (turnaround_score + news_sentiment) / 2
        
        score += turnaround_score * weights["turnaround_potential"]
        
        return round(score * 100, 1)