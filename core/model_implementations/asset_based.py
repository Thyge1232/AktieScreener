from typing import Dict, Any

class AssetBasedValuation:
    """Aktivbaseret Vurdering"""
    
    def calculate(self, metrics: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        # Hent nødvendige metrikker
        tangible_assets = metrics.get("tangible_assets")
        liabilities = metrics.get("total_liabilities")
        excess_cash = metrics.get("excess_cash", 0)
        
        if not tangible_assets or not liabilities:
            return {"error": "Mangler tangible_assets eller total_liabilities"}
        
        # Anvend eventuelle justeringer fra parametre
        liability_adjustment = params.get("liability_adjustment", 0)
        adjusted_liabilities = liabilities * (1 + liability_adjustment)
        
        # Beregn nettoaktiver
        net_assets = tangible_assets - adjusted_liabilities + excess_cash
        
        # Beregn værdi per aktie
        shares_outstanding = metrics.get("shares_outstanding", 1)
        fair_value_per_share = net_assets / shares_outstanding
        
        # Hent aktuel pris
        current_price = metrics.get("current_price", 0)
        
        # Margin of safety
        margin_of_safety = 0
        if current_price > 0:
            margin_of_safety = (fair_value_per_share - current_price) / fair_value_per_share
        
        return {
            "fair_value_per_share": fair_value_per_share,
            "current_price": current_price,
            "margin_of_safety": margin_of_safety,
            "net_assets": net_assets,
            "excess_cash": excess_cash,
            "assumptions": params,
            "model": "asset_based"
        }
    
    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "Aktivbaseret Vurdering",
            "description": "Beregner værdi baseret på virksomhedens reelle aktiver",
            "category": "deep_value",
            "required_parameters": [
                "tangible_book_value",
                "excess_cash",
                "liabilities"
            ]
        }