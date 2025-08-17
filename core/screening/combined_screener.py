from typing import Dict, List, Any

class CombinedScreener:
    """Kombineret screening logik for GARP og lignende strategier"""
    
    def __init__(self, data_fetcher):
        self.data_fetcher = data_fetcher
    
    def _passes_filters(self, metrics: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Tjekker om aktien opfylder kombinerede profil-kriterier"""
        # Markedsværdi
        market_cap = metrics.get("market_cap", 0)
        if not (params["min_market_cap"] <= market_cap <= params["max_market_cap"]):
            return False
        
        # Vækstkrav
        revenue_growth = metrics.get("revenue_growth")
        eps_growth = metrics.get("eps_growth")
        
        revenue_ok = revenue_growth is not None and revenue_growth >= params.get("min_revenue_growth", 0)
        eps_ok = eps_growth is not None and eps_growth >= params.get("min_eps_growth", 0)
        
        if params.get("require_both_growth", True):
            if not (revenue_ok and eps_ok):
                return False
        else:
            if not (revenue_ok or eps_ok):
                return False
        
        # Bruttomargen
        gross_margin = metrics.get("gross_margin")
        if gross_margin is not None and gross_margin < params.get("min_gross_margin", 0):
            return False
        
        # PE Ratio
        pe_ratio = metrics.get("pe_ratio")
        if pe_ratio and pe_ratio > params.get("max_pe_ratio", float('inf')):
            return False
        
        # PB Ratio
        pb_ratio = metrics.get("pb_ratio")
        if pb_ratio and pb_ratio > params.get("max_pb_ratio", float('inf')):
            return False
        
        # ROE
        roe = metrics.get("roe")
        if roe and roe < params.get("min_roe", 0):
            return False
        
        return True