from typing import Dict, List, Any

def analyze_sector_potential() -> Dict[str, float]:
    """Returnerer sektorer med højest potentiale for multibaggers baseret på historiske data"""
    sector_potential = {
        'Technology': 9.5,
        'Healthcare': 8.8,
        'Consumer Cyclical': 7.5,
        'Communication Services': 8.0,
        'Industrials': 6.5,
        'Financial Services': 5.0,
        'Consumer Defensive': 5.5,
        'Energy': 4.0,
        'Utilities': 3.5,
        'Basic Materials': 6.0,
        'Real Estate': 4.5
    }
    return sector_potential

def get_sector_leader(sector: str, companies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Finder den bedste virksomhed i en given sektor baseret på kvalitetsscore"""
    sector_companies = [c for c in companies if c.get("sector") == sector]
    
    if not sector_companies:
        return None
    
    # Sorter efter kvalitetsscore
    sector_companies.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
    
    return sector_companies[0]

def identify_sector_trends(market_data: Dict[str, Any]) -> Dict[str, str]:
    """Identificerer nuværende sektortrends baseret på markedets adfærd"""
    trends = {}
    
    # Dette er en placeholder - i virkeligheden ville du bruge avanceret analyse
    for sector in market_data.get("sectors", []):
        performance = sector.get("performance", 0)
        
        if performance > 0.15:
            trends[sector["name"]] = "Strong Uptrend"
        elif performance > 0.05:
            trends[sector["name"]] = "Moderate Uptrend"
        elif performance > -0.05:
            trends[sector["name"]] = "Sideways"
        elif performance > -0.15:
            trends[sector["name"]] = "Moderate Downtrend"
        else:
            trends[sector["name"]] = "Strong Downtrend"
    
    return trends

def calculate_sector_rotation_score(portfolio: List[Dict[str, Any]], market_data: Dict[str, Any]) -> float:
    """Beregner en score for porteføljens sektorallokering i forhold til markedstrends"""
    # Identificer nuværende trends
    trends = identify_sector_trends(market_data)
    
    # Tæl antal aktier i hver trendkategori
    trend_counts = {"Strong Uptrend": 0, "Moderate Uptrend": 0, "Sideways": 0, "Moderate Downtrend": 0, "Strong Downtrend": 0}
    
    for asset in portfolio:
        sector = asset.get("sector")
        if sector in trends:
            trend = trends[sector]
            trend_counts[trend] += 1
    
    # Beregn score (højere er bedre)
    total_assets = len(portfolio)
    if total_assets == 0:
        return 0
    
    score = (
        (trend_counts["Strong Uptrend"] * 1.0 + 
         trend_counts["Moderate Uptrend"] * 0.7 +
         trend_counts["Sideways"] * 0.3) / total_assets
    )
    
    return score

def get_sector_recommendations(portfolio: List[Dict[str, Any]], market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Genererer sektor-anbefalinger baseret på markedstrends og portefølje"""
    trends = identify_sector_trends(market_data)
    
    # Find sektorer i stærk opadgående trend
    strong_trends = [sector for sector, trend in trends.items() if trend == "Strong Uptrend"]
    
    # Find sektorer i porteføljen
    portfolio_sectors = set([asset["sector"] for asset in portfolio if "sector" in asset])
    
    # Generer anbefalinger
    recommendations = []
    
    # Anbefal sektorer i stærk trend som ikke er i porteføljen
    for sector in strong_trends:
        if sector not in portfolio_sectors:
            recommendations.append({
                "type": "BUY",
                "sector": sector,
                "rationale": "Sektoren viser stærk opadgående trend og er ikke repræsenteret i porteføljen"
            })
    
    # Anbefal reduktion af sektorer i nedadgående trend
    for asset in portfolio:
        sector = asset.get("sector")
        if sector and trends.get(sector) in ["Strong Downtrend", "Moderate Downtrend"]:
            recommendations.append({
                "type": "SELL",
                "sector": sector,
                "rationale": f"Sektoren viser {trends[sector].lower()} og bør reduceres"
            })
    
    return recommendations