from typing import Dict, List, Any

class MultibaggerScreener:
    """Multibagger-specifik screening logik"""
    
    def __init__(self, data_fetcher):
        self.data_fetcher = data_fetcher
    
    def screen(self, tickers: List[str], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Screening med en specifik multibagger-profil"""
        results = []
        params = profile["parameters"]
        
        for ticker in tickers:
            metrics = self.data_fetcher.fetch_all_metrics(ticker, "multibagger")
            if not metrics:
                continue
                
            if self._passes_filters(metrics, params):
                # Beregn multibagger-score
                metrics["multibagger_score"] = self._calculate_score(metrics, profile)
                results.append(metrics)
        
        # Sorter efter multibagger-score
        results.sort(key=lambda x: x["multibagger_score"], reverse=True)
        return results
    
    def _passes_filters(self, metrics: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Tjekker om aktien opfylder multibagger-profilens kriterier"""
        # Markedsværdi
        market_cap = metrics.get("market_cap", 0)
        if not (params["min_market_cap"] <= market_cap <= params["max_market_cap"]):
            return False
        
        # Vækstkrav
        revenue_ok = metrics.get("revenue_growth") is not None and metrics["revenue_growth"] >= params["min_revenue_growth"]
        eps_ok = metrics.get("eps_growth") is not None and metrics["eps_growth"] >= params["min_eps_growth"]
        
        if params.get("require_both_growth", True):
            if not (revenue_ok and eps_ok):
                return False
        else:
            if not (revenue_ok or eps_ok):
                return False
        
        # Bruttomargen
        gross_margin = metrics.get("gross_margin")
        if gross_margin is not None and gross_margin < params["min_gross_margin"]:
            return False
        
        # Gældskriterier
        debt_to_equity = metrics.get("debt_to_equity")
        if debt_to_equity is not None and debt_to_equity > params["max_debt_to_equity"]:
            return False
            
        debt_to_ebitda = metrics.get("debt_to_ebitda")
        if debt_to_ebitda is not None and debt_to_ebitda > params["max_debt_to_ebitda"]:
            return False
        
        interest_coverage = metrics.get("interest_coverage")
        if interest_coverage is not None and interest_coverage < params.get("min_interest_coverage", 0):
            return False
        
        # PEG Ratio
        peg_ratio = metrics.get("peg_ratio")
        if peg_ratio is not None and peg_ratio > params["max_peg_ratio"]:
            return False
        
        # ROE
        roe = metrics.get("roe")
        if roe is not None and roe < params["min_roe"]:
            return False
        
        # Tekniske kriterier (kun for momentum-profil)
        if "min_price_above_sma50" in params:
            price_above_sma50 = metrics.get("price_above_sma50")
            if params["min_price_above_sma50"] and not price_above_sma50:
                return False
            
            rsi = metrics.get("rsi")
            if rsi is not None:
                if "min_rsi" in params and rsi < params["min_rsi"]:
                    return False
                if "max_rsi" in params and rsi > params["max_rsi"]:
                    return False
            
            volume_surge = metrics.get("volume_surge")
            if "min_volume_surge" in params and volume_surge and volume_surge < params["min_volume_surge"]:
                return False
        
        return True
    
    def _calculate_score(self, metrics: Dict[str, Any], profile: Dict[str, Any]) -> float:
        """Beregner en samlet multibagger-score"""
        params = profile["parameters"]
        weights = {
            "revenue_growth": 0.20,
            "eps_growth": 0.20,
            "roe": 0.15,
            "gross_margin": 0.10,
            "debt_safety": 0.10,
            "peg_ratio": 0.10,
            "technical": 0.15
        }
        
        score = 0
        
        # Revenue vækst score
        if metrics["revenue_growth"] is not None:
            revenue_score = min(1.0, metrics["revenue_growth"] / (params["min_revenue_growth"] * 2))
            score += revenue_score * weights["revenue_growth"]
        
        # EPS vækst score
        if metrics["eps_growth"] is not None:
            eps_score = min(1.0, metrics["eps_growth"] / (params["min_eps_growth"] * 2))
            score += eps_score * weights["eps_growth"]
        
        # ROE score
        if metrics["roe"] is not None:
            roe_score = min(1.0, metrics["roe"] / max(0.01, params["min_roe"] * 1.5))
            score += roe_score * weights["roe"]
        
        # Bruttomargen score
        if metrics["gross_margin"] is not None:
            margin_score = min(1.0, metrics["gross_margin"] / max(0.01, params["min_gross_margin"] * 1.2))
            score += margin_score * weights["gross_margin"]
        
        # Gældssikkerhed score
        debt_safety = 1.0
        if metrics["debt_to_equity"] is not None and metrics["debt_to_equity"] > 0:
            debt_safety = max(0, 1 - (metrics["debt_to_equity"] / params["max_debt_to_equity"]))
        if metrics["debt_to_ebitda"] is not None and metrics["debt_to_ebitda"] > 0:
            debt_safety = min(debt_safety, max(0, 1 - (metrics["debt_to_ebitda"] / params["max_debt_to_ebitda"])))
        if metrics["interest_coverage"] is not None and metrics["interest_coverage"] > 0:
            ic_score = min(1.0, metrics["interest_coverage"] / params["min_interest_coverage"])
            debt_safety = (debt_safety + ic_score) / 2
        score += debt_safety * weights["debt_safety"]
        
        # PEG Ratio score (lavere er bedre)
        if metrics["peg_ratio"] is not None and metrics["peg_ratio"] > 0:
            peg_score = max(0, 1 - (metrics["peg_ratio"] / max(1.0, params["max_peg_ratio"])))
            score += peg_score * weights["peg_ratio"]
        
        # Teknisk score (hvis relevant)
        if "min_price_above_sma50" in params:
            technical_score = 0
            if metrics.get("price_above_sma50"):
                technical_score += 0.4
                
            rsi = metrics.get("rsi")
            if rsi is not None:
                if "min_rsi" in params and "max_rsi" in params:
                    rsi_score = min(1.0, max(0, (rsi - params["min_rsi"]) / (params["max_rsi"] - params["min_rsi"])))
                    technical_score += rsi_score * 0.4
            
            volume_surge = metrics.get("volume_surge")
            if volume_surge and "min_volume_surge" in params:
                volume_score = min(1.0, volume_surge / params["min_volume_surge"])
                technical_score += volume_score * 0.2
            
            score += technical_score * weights["technical"]
        
        return round(score * 100, 1)