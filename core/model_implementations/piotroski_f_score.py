from typing import Dict, Any

class PiotroskiFScore:
    """Piotroski F-Score - Kvalitetsvurdering baseret på 9 finansielle kriterier"""
    
    def calculate(self, metrics: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        # Tjek om vi har alle nødvendige metrikker
        required_metrics = [
            "net_income", "operating_cash_flow", "long_term_debt",
            "current_ratio", "gross_margin", "asset_turnover",
            "roe", "share_issuance", "gross_margin_change", "asset_turnover_change"
        ]
        
        for metric in required_metrics:
            if metric not in metrics:
                return {"error": f"Mangler metrik: {metric} for Piotroski F-Score beregning"}
        
        # Beregn F-Score (0-9)
        f_score = 0
        
        # Profitabilitet (0-4 point)
        if metrics["net_income"] > 0:
            f_score += 1
            
        if metrics["roe"] > 0:
            f_score += 1
            
        if metrics["operating_cash_flow"] > 0:
            f_score += 1
            
        if metrics["operating_cash_flow"] > metrics["net_income"]:
            f_score += 1
        
        # Finansiel styrke (0-4 point)
        if metrics["long_term_debt"] < metrics.get("long_term_debt_prev", float('inf')):
            f_score += 1
            
        if metrics["current_ratio"] > metrics.get("current_ratio_prev", 0):
            f_score += 1
            
        if metrics["share_issuance"] <= 0:  # Ingen nye aktier udstedt
            f_score += 1
            
        if metrics["gross_margin"] > metrics.get("gross_margin_prev", 0):
            f_score += 1
        
        # Operations effektivitet (0-1 point)
        if metrics["asset_turnover"] > metrics.get("asset_turnover_prev", 0):
            f_score += 1
        
        # Returner resultat
        return {
            "f_score": f_score,
            "max_score": 9,
            "quality_rating": self._get_quality_rating(f_score),
            "model": "piotroski_f_score"
        }
    
    def _get_quality_rating(self, f_score: int) -> str:
        """Returnerer en kvalitetsvurdering baseret på F-Score"""
        if f_score >= 8:
            return "Meget Høj"
        elif f_score >= 6:
            return "Høj"
        elif f_score >= 4:
            return "Medium"
        elif f_score >= 2:
            return "Lav"
        else:
            return "Meget Lav"
    
    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "Piotroski F-Score",
            "description": "Beregner kvalitetsvurdering baseret på 9 finansielle kriterier",
            "category": "quality",
            "required_parameters": [
                "net_income",
                "operating_cash_flow",
                "long_term_debt",
                "current_ratio",
                "gross_margin",
                "asset_turnover"
            ]
        }