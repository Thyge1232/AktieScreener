from typing import Dict, Any

class DiscountedCashFlow:
    """Diskonteret Kontantstrøm (DCF) model"""
    
    def calculate(self, metrics: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        # Standardparametre hvis ikke angivet
        default_params = {
            "growth_rate_short_term": 0.05,
            "growth_rate_long_term": 0.02,
            "discount_rate": 0.08,
            "terminal_growth_rate": 0.025,
            "years_short_term": 5,
            "years_long_term": 10
        }
        
        if params:
            default_params.update(params)
        params = default_params
        
        # Hent nødvendige metrikker
        fcf = metrics.get("free_cash_flow")
        if not fcf:
            # Prøv at beregne FCF fra cashflow
            try:
                cashflow = metrics.get("cashflow", {})
                if cashflow and "Total Cash From Operating Activities" in cashflow and "Capital Expenditures" in cashflow:
                    operating_cash_flow = cashflow["Total Cash From Operating Activities"]
                    capex = cashflow["Capital Expenditures"]
                    fcf = operating_cash_flow + capex  # Capex er normalt negativ
            except:
                pass
            
            if not fcf:
                return {"error": "Mangler free_cash_flow for DCF beregning"}
        
        # Hent andre nødvendige metrikker
        net_debt = metrics.get("net_debt", 0)
        shares_outstanding = metrics.get("shares_outstanding", 1)
        current_price = metrics.get("current_price", 0)
        
        # Beregn kortvarig vækst
        short_term_value = 0
        fcf_projected = fcf
        for i in range(1, params["years_short_term"] + 1):
            fcf_projected *= (1 + params["growth_rate_short_term"])
            discount_factor = (1 + params["discount_rate"]) ** i
            short_term_value += fcf_projected / discount_factor
        
        # Beregn langvarig vækst (terminalværdi)
        terminal_fcf = fcf_projected * (1 + params["terminal_growth_rate"])
        terminal_value = terminal_fcf / (params["discount_rate"] - params["terminal_growth_rate"])
        terminal_value_discounted = terminal_value / ((1 + params["discount_rate"]) ** params["years_short_term"])
        
        # Samlet virksomhedsværdi
        total_value = short_term_value + terminal_value_discounted
        
        # Juster for gæld og kontanter
        equity_value = total_value - net_debt
        fair_value_per_share = equity_value / shares_outstanding
        
        # Beregn margin of safety
        margin_of_safety = 0
        if current_price > 0:
            margin_of_safety = (fair_value_per_share - current_price) / fair_value_per_share
        
        return {
            "fair_value_per_share": fair_value_per_share,
            "current_price": current_price,
            "margin_of_safety": margin_of_safety,
            "short_term_value": short_term_value,
            "terminal_value": terminal_value_discounted,
            "assumptions": params,
            "model": "discounted_cash_flow"
        }
    
    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "Diskonteret Kontantstrøm (DCF)",
            "description": "Beregner virksomhedens værdi baseret på fremtidige kontantstrømme",
            "category": "fundamental",
            "required_parameters": [
                "free_cash_flow",
                "growth_rate_short_term",
                "growth_rate_long_term",
                "discount_rate",
                "terminal_growth_rate"
            ]
        }