from typing import Dict, Any

class ResidualIncomeModel:
    """Residual Indkomst Model"""
    
    def calculate(self, metrics: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        # Standardparametre hvis ikke angivet
        default_params = {
            "cost_of_equity": 0.09
        }
        
        if params:
            default_params.update(params)
        params = default_params
        
        # Hent nødvendige metrikker
        book_value = metrics.get("book_value")
        roe = metrics.get("roe")
        
        if not book_value or not roe:
            return {"error": "Mangler book_value eller roe for Residual Income beregning"}
        
        # Hent andre nødvendige metrikker
        current_price = metrics.get("current_price", 0)
        
        # Beregn residual indkomst
        residual_income = book_value * (roe - params["cost_of_equity"])
        
        # Beregn værdi
        if roe > params["cost_of_equity"]:
            # Vækstmodel
            growth_rate = params.get("growth_rate", 0.02)
            fair_value = book_value + (residual_income / (params["cost_of_equity"] - growth_rate))
        else:
            # Ingen vækst
            fair_value = book_value + (residual_income / params["cost_of_equity"])
        
        # Margin of safety
        margin_of_safety = 0
        if current_price > 0:
            margin_of_safety = (fair_value - current_price) / fair_value
        
        return {
            "fair_value_per_share": fair_value,
            "current_price": current_price,
            "margin_of_safety": margin_of_safety,
            "residual_income": residual_income,
            "assumptions": params,
            "model": "residual_income"
        }
    
    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "Residual Indkomst Model",
            "description": "Beregner værdi baseret på overskudsafkastet over kapitalkost",
            "category": "fundamental",
            "required_parameters": [
                "book_value",
                "roe",
                "cost_of_equity"
            ]
        }