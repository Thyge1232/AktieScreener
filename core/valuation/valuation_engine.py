from typing import Dict, Any, Optional

class ValuationEngine:
    """Avanceret værdiansættelse med strategi-justering"""

    def __init__(self):
        # Initialiser modeller senere for at undgå cirkulære imports
        self.models = None

    def initialize_models(self):
        """Initialiserer modeller (kaldes først når de faktisk er nødvendige)"""
        if self.models is None:
            from core.model_implementations.discounted_cash_flow import DiscountedCashFlow
            from core.model_implementations.dividend_discount import DividendDiscountModel
            from core.model_implementations.residual_income import ResidualIncomeModel
            from core.model_implementations.asset_based import AssetBasedValuation
            from core.model_implementations.piotroski_f_score import PiotroskiFScore
            
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
        self.initialize_models()

        if model_name not in self.models:
            return {"error": f"Ukendt værdiansættelsesmodel: {model_name}"}

        strategy_params = self._get_strategy_params(strategy_type, model_name)
        if params:
            strategy_params.update(params)

        result = self.models[model_name].calculate(metrics, strategy_params)

        if strategy_type == "multibagger" and model_name in ["discounted_cash_flow", "residual_income"]:
            result = self._adjust_for_growth(result, metrics)
        elif strategy_type == "value" and model_name in ["discounted_cash_flow", "dividend_discount"]:
            result = self._adjust_for_safety(result, metrics)
        elif strategy_type == "deep_value" and model_name in ["asset_based", "piotroski_f_score"]:
            result = self._adjust_for_asset_value(result, metrics)

        return result

    def _get_strategy_params(self, strategy_type: str, model_name: str) -> Dict[str, Any]:
        """Returnerer strategi-justerede standardparametre"""
        strategy_params = {}

        if strategy_type == "multibagger":
            if model_name == "discounted_cash_flow":
                strategy_params = {
                    "growth_rate_short_term": 0.07,
                    "growth_rate_long_term": 0.03,
                    "terminal_growth_rate": 0.03
                }
            elif model_name == "residual_income":
                strategy_params = {"cost_of_equity": 0.10}

        elif strategy_type == "value":
            if model_name == "discounted_cash_flow":
                strategy_params = {
                    "growth_rate_short_term": 0.04,
                    "growth_rate_long_term": 0.02,
                    "terminal_growth_rate": 0.02
                }
            elif model_name == "dividend_discount":
                strategy_params = {"dividend_growth_rate": 0.025}

        elif strategy_type == "deep_value":
            if model_name == "asset_based":
                strategy_params = {"liability_adjustment": 0.1}
            elif model_name == "piotroski_f_score":
                strategy_params = {"min_score": 6}

        return strategy_params

    def _adjust_for_growth(self, result: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Justerer DCF-resultater for vækstaktier"""
        revenue_growth = metrics.get("revenue_growth", 0)
        eps_growth = metrics.get("eps_growth", 0)
        avg_growth = (revenue_growth + eps_growth) / 2 if revenue_growth and eps_growth else max(revenue_growth, eps_growth)
        growth_factor = 1 + (avg_growth * 0.5)
        if "fair_value_per_share" in result:
            result["fair_value_per_share"] *= growth_factor

        if "current_price" in result and result["current_price"] > 0 and "fair_value_per_share" in result:
            result["margin_of_safety"] = (result["fair_value_per_share"] - result["current_price"]) / result["fair_value_per_share"]

        return result

    def _adjust_for_safety(self, result: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Justerer værdiansættelse for value-aktier med ekstra sikkerhedsmargin"""
        pb_ratio = metrics.get("pb_ratio", 2.0)
        pe_ratio = metrics.get("pe_ratio", 20.0)
        safety_margin = max(0.15, 1 - min(pb_ratio / 1.5, pe_ratio / 12.0))

        if "margin_of_safety" in result:
            result["margin_of_safety"] = min(1.0, result["margin_of_safety"] + safety_margin)

        return result

    def _adjust_for_asset_value(self, result: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Justerer værdiansættelse for deep value-aktier med fokus på aktiver"""
        tangible_book_value = metrics.get("price_to_tangible_book", 0)
        cash_to_market_cap = metrics.get("cash_to_market_cap", 0)

        if "fair_value_per_share" in result and tangible_book_value > 0:
            asset_factor = 1 + (0.75 * (1 - tangible_book_value))
            result["fair_value_per_share"] *= asset_factor

        if "fair_value_per_share" in result and cash_to_market_cap > 0.3:
            result["fair_value_per_share"] *= (1 + cash_to_market_cap)

        if "current_price" in result and result["current_price"] > 0 and "fair_value_per_share" in result:
            result["margin_of_safety"] = (result["fair_value_per_share"] - result["current_price"]) / result["fair_value_per_share"]

        return result

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Returnerer information om en specifik model"""
        self.initialize_models()
        if model_name not in self.models:
            return {"error": f"Ukendt værdiansættelsesmodel: {model_name}"}
        return self.models[model_name].get_info()