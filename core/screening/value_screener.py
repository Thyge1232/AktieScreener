from typing import Dict, Any, Optional
from core.model_implementations.discounted_cash_flow import DiscountedCashFlow
from core.model_implementations.dividend_discount import DividendDiscountModel
from core.model_implementations.residual_income import ResidualIncomeModel
from core.model_implementations.asset_based import AssetBasedValuation
from core.model_implementations.piotroski_f_score import PiotroskiFScore

class ValuationEngine:
    """Avanceret værdiansættelse med strategi-justering"""
    
    def __init__(self):
        self.models = {
            "discounted_cash_flow": DiscountedCashFlow(),
            "dividend_discount": DividendDiscountModel(),
            "residual_income": ResidualIncomeModel(),
            "asset_based": AssetBasedValuation(),
            "piotroski_f_score": PiotroskiFScore()
        }
    
    def evaluate(self, metrics: Dict[str, Any], strategy_type: str, 
                model_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Udfører strategi-justeret værdiansættelse"""
        # Tjek om modellen findes
        if model_name not in self.models:
            return {"error": f"Ukendt værdiansættelsesmodel: {model_name}"}
        
        # Hent strategispecifikke standardparametre
        strategy_params = self._get_strategy_params(strategy_type, model_name)
        
        # Opdater med brugerdefinerede parametre
        if params:
            strategy_params.update(params)
        
        # Udfør beregning
        result = self.models[model_name].calculate(metrics, strategy_params)
        
        # Strategi-specifik justering af resultater
        if strategy_type == "multibagger" and model_name in ["discounted_cash_flow", "residual_income"]:
            result = self._adjust_for_growth(result, metrics)
        elif strategy_type == "value" and model_name in ["discounted_cash_flow", "dividend_discount"]:
            result = self._adjust_for_safety(result, metrics)
        elif strategy_type == "deep_value" and model_name in ["asset_based", "piotroski_f_score"]:
            result = self._adjust_for_asset_value(result, metrics)
        
        return result
    
    def _get_strategy_params(self, strategy_type: str, model_name: str) -> Dict[str, Any]:
        """Returnerer strategi-justerede standardparametre"""
        # Dette ville normalt hente parametre fra config/valuation/strategy_specific_params.json
        strategy_params = {}
        
        # Standardparametre for multibagger
        if strategy_type == "multibagger":
            if model_name == "discounted_cash_flow":
                strategy_params = {
                    "growth_rate_short_term": 0.07,
                    "growth_rate_long_term": 0.03,
                    "terminal_growth_rate": 0.03
                }
            elif model_name == "residual_income":
                strategy_params = {"cost_of_equity": 0.10}
        
        # Standardparametre for value
        elif strategy_type == "value":
            if model_name == "discounted_cash_flow":
                strategy_params = {
                    "growth_rate_short_term": 0.04,
                    "growth_rate_long_term": 0.02,
                    "terminal_growth_rate": 0.02
                }
            elif model_name == "dividend_discount":
                strategy_params = {"dividend_growth_rate": 0.025}
        
        # Standardparametre for deep value
        elif strategy_type == "deep_value":
            if model_name == "asset_based":
                strategy_params = {"liability_adjustment": 0.1}
            elif model_name == "piotroski_f_score":
                strategy_params = {"min_score": 6}
        
        return strategy_params
    
    def _adjust_for_growth(self, result: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Justerer DCF-resultater for vækstaktier"""
        # Højere vækstjustering for multibaggers
        revenue_growth = metrics.get("revenue_growth", 0)
        eps_growth = metrics.get("eps_growth", 0)
        avg_growth = (revenue_growth + eps_growth) / 2 if revenue_growth and eps_growth else max(revenue_growth, eps_growth)
        
        # Justering baseret på vækst
        growth_factor = 1 + (avg_growth * 0.5)
        result["fair_value_per_share"] *= growth_factor
        
        # Opdater margin of safety
        if "current_price" in result and result["current_price"] > 0:
            result["margin_of_safety"] = (result["fair_value_per_share"] - result["current_price"]) / result["fair_value_per_share"]
        
        return result
    
    def _adjust_for_safety(self, result: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Justerer værdiansættelse for value-aktier med ekstra sikkerhedsmargin"""
        # Tilføj ekstra sikkerhedsmargin for value-aktier
        pb_ratio = metrics.get("pb_ratio", 2.0)
        pe_ratio = metrics.get("pe_ratio", 20.0)
        
        # Beregn sikkerhedsmargin baseret på værdimetrikker
        safety_margin = max(0.15, 1 - min(pb_ratio / 1.5, pe_ratio / 12.0))
        
        # Juster margin of safety
        if "margin_of_safety" in result:
            result["margin_of_safety"] = min(1.0, result["margin_of_safety"] + safety_margin)
        
        return result
    
    def _adjust_for_asset_value(self, result: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Justerer værdiansættelse for deep value-aktier med fokus på aktiver"""
        # For deep value, fokuser på tangibelt bogføringsværdi
        tangible_book_value = metrics.get("price_to_tangible_book", 0)
        cash_to_market_cap = metrics.get("cash_to_market_cap", 0)
        
        # Justering baseret på aktivværdi
        if tangible_book_value > 0:
            asset_factor = 1 + (0.75 * (1 - tangible_book_value))
            result["fair_value_per_share"] *= asset_factor
        
        # Hvis der er meget kontanter, tilføj ekstra værdi
        if cash_to_market_cap > 0.3:
            result["fair_value_per_share"] *= (1 + cash_to_market_cap)
        
        # Opdater margin of safety
        if "current_price" in result and result["current_price"] > 0:
            result["margin_of_safety"] = (result["fair_value_per_share"] - result["current_price"]) / result["fair_value_per_share"]
        
        return result
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Returnerer information om en specifik model"""
        if model_name not in self.models:
            return {"error": f"Ukendt værdiansættelsesmodel: {model_name}"}
        
        return self.models[model_name].get_info()

from typing import Dict, List, Any, Optional

class ValueScreener:
    """Value-specifik screening logik"""
    
    def __init__(self, data_fetcher):
        self.data_fetcher = data_fetcher
    
    def screen(self, tickers: List[str], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Screening med en specifik value-profil"""
        results = []
        params = profile["parameters"]
        
        for ticker in tickers:
            metrics = self.data_fetcher.fetch_all_metrics(ticker, "value")
            if not metrics:
                continue
                
            if self._passes_filters(metrics, params):
                # Beregn value-score
                metrics["value_score"] = self._calculate_score(metrics, profile)
                results.append(metrics)
        
        # Sorter efter value-score
        results.sort(key=lambda x: x["value_score"], reverse=True)
        return results
    
    def _passes_filters(self, metrics: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Tjekker om aktien opfylder value-profilens kriterier"""
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
        
        # Dividendeafkast
        dividend_yield = metrics.get("dividend_yield", 0)
        if dividend_yield < params.get("min_dividend_yield", 0):
            return False
        
        # Gældskriterier
        debt_to_equity = metrics.get("debt_to_equity")
        if debt_to_equity and debt_to_equity > params["max_debt_to_equity"]:
            return False
            
        interest_coverage = metrics.get("interest_coverage")
        if interest_coverage and interest_coverage < params.get("min_interest_coverage", 0):
            return False
        
        # Likviditetskriterier
        current_ratio = metrics.get("current_ratio")
        if current_ratio and current_ratio < params.get("min_current_ratio", 0):
            return False
        
        # ROE
        roe = metrics.get("roe")
        if roe and roe < params["min_roe"]:
            return False
        
        # EPS-konsistens
        positive_eps_years = metrics.get("positive_eps_years")
        if positive_eps_years and positive_eps_years < params.get("min_positive_eps_years", 0):
            return False
        
        # Sektorbegrænsninger (for cyclical)
        if "cyclical_industries" in params and metrics["sector"] not in params["cyclical_industries"]:
            return False
            
        return True
    
    def _calculate_score(self, metrics: Dict[str, Any], profile: Dict[str, Any]) -> float:
        """Beregner en samlet value-score"""
        params = profile["parameters"]
        weights = {
            "pe_ratio": 0.25,
            "pb_ratio": 0.25,
            "ev_ebitda": 0.20,
            "dividend_yield": 0.15,
            "financial_health": 0.15
        }
        
        score = 0
        
        # PE Ratio score (lavere er bedre)
        if metrics["pe_ratio"] and params["max_pe_ratio"]:
            pe_score = min(1.0, (params["max_pe_ratio"] / metrics["pe_ratio"]))
            score += pe_score * weights["pe_ratio"]
        
        # PB Ratio score
        if metrics["pb_ratio"] and params["max_pb_ratio"]:
            pb_score = min(1.0, (params["max_pb_ratio"] / metrics["pb_ratio"]))
            score += pb_score * weights["pb_ratio"]
        
        # EV/EBITDA score
        if metrics["ev_ebitda"] and params["max_ev_ebitda"]:
            ev_score = min(1.0, (params["max_ev_ebitda"] / metrics["ev_ebitda"]))
            score += ev_score * weights["ev_ebitda"]
        
        # Dividendeafkast score
        if metrics["dividend_yield"] and "min_dividend_yield" in params:
            div_score = min(1.0, (metrics["dividend_yield"] / params["min_dividend_yield"]))
            score += div_score * weights["dividend_yield"]
        
        # Finansiel sundhedsscore
        health_score = 1.0
        if metrics["debt_to_equity"] and params["max_debt_to_equity"]:
            health_score *= max(0, 1 - (metrics["debt_to_equity"] / params["max_debt_to_equity"]))
        if metrics["current_ratio"] and "min_current_ratio" in params:
            health_score *= min(1.0, (metrics["current_ratio"] / params["min_current_ratio"]))
        if metrics["roe"] and params["min_roe"]:
            health_score *= min(1.0, (metrics["roe"] / params["min_roe"]))
        
        score += health_score * weights["financial_health"]
        
        return round(score * 100, 1)