from typing import Dict, Any

class DividendDiscountModel:
    """Dividende Diskonteringsmodel (DDM)"""
    
    def calculate(self, metrics: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        # Standardparametre hvis ikke angivet
        default_params = {
            "dividend_growth_rate": 0.03,
            "required_return": 0.07
        }
        
        if params:
            default_params.update(params)
        params = default_params
        
        # Hent nødvendige metrikker
        dividend = metrics.get("dividend")
        if not dividend:
            # Prøv at beregne fra annualeret dividende
            try:
                dividends = metrics.get("dividends", {})
                if dividends and len(dividends) > 0:
                    latest_dividend = dividends.iloc[0]
                    shares_outstanding = metrics.get("shares_outstanding", 1)
                    dividend = latest_dividend / shares_outstanding
            except:
                pass
            
            if not dividend:
                return {"error": "Mangler dividend for DDM beregning"}
        
        # Hent andre nødvendige metrikker
        current_price = metrics.get("current_price", 0)
        
        # Gordon Growth Model
        try:
            fair_value = dividend / (params["required_return"] - params["dividend_growth_rate"])
        except ZeroDivisionError:
            return {"error": "Ugyldig parameterkombination: required_return må ikke være lig dividend_growth_rate"}
        
        # Margin of safety
        margin_of_safety = 0
        if current_price > 0:
            margin_of_safety = (fair_value - current_price) / fair_value
        
        return {
            "fair_value_per_share": fair_value,
            "current_price": current_price,
            "margin_of_safety": margin_of_safety,
            "assumptions": params,
            "model": "dividend_discount"
        }
    
    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "Dividende Diskonteringsmodel (DDM)",
            "description": "Beregner aktiens værdi baseret på fremtidige dividender",
            "category": "income",
            "required_parameters": [
                "dividend",
                "dividend_growth_rate",
                "required_return"
            ]
        }