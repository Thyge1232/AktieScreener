# Øverst i filen
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class ValuationConfig:
    """Central konfiguration for alle finansielle antagelser."""
    
    # --- Generelle Markedsantagelser ---
    risk_free_rate: float = 0.04
    market_premium: float = 0.06
    default_tax_rate: float = 0.25
    terminal_growth_cap: float = 0.05
    
    # --- DCF-specifikke Parametre ---
    dcf_projection_years_default: int = 10
    dcf_fade_factor: float = 0.85
    dcf_terminal_growth_buffer_factor: float = 0.8
    dcf_high_growth_years_cap: int = 5
    dcf_transition_years_cap: int = 3
    monte_carlo_simulations_default: int = 100
    monte_carlo_performance_limit: int = 100 # Antal simuleringer i GUI-visning
    
    # --- Vægtninger for Værdiansættelsesmetoder ---
    valuation_weights: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'mature': {'dcf': 0.5, 'pe': 0.2, 'ev_ebitda': 0.2, 'pb': 0.1},
        'growth': {'dcf': 0.6, 'pe': 0.2, 'ev_ebitda': 0.2, 'pb': 0.0},
        'startup': {'dcf': 0.4, 'pe': 0.3, 'ev_ebitda': 0.3, 'pb': 0.0},
        'bank': {'dcf': 0.0, 'pe': 0.4, 'ev_ebitda': 0.0, 'pb': 0.6},
        'reit': {'dcf': 0.2, 'pe': 0.2, 'ev_ebitda': 0.2, 'pb': 0.4},
        'utility': {'dcf': 0.4, 'pe': 0.2, 'ev_ebitda': 0.2, 'pb': 0.2},
        'cyclical': {'dcf': 0.3, 'pe': 0.3, 'ev_ebitda': 0.3, 'pb': 0.1},
        # Default fallback
        'default': {'dcf': 0.5, 'pe': 0.2, 'ev_ebitda': 0.2, 'pb': 0.1}
    })
    
    # --- Standardmultipla for Sammenligningsværdiansættelse ---
    comparable_pe_default: float = 15.0
    comparable_ev_ebitda_default: float = 10.0
    comparable_pb_default: float = 2.0
    comparable_growth_threshold_high: float = 0.05
    comparable_growth_premium_factor_pe: float = 2.0
    comparable_growth_premium_factor_ev_ebitda: float = 1.5
    comparable_roe_premium_threshold: float = 0.15
    
    # --- Risikovurderingsparametre ---
    # Grænser for samlet risikoscore
    risk_score_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'very_high': 75,
        'high': 55,
        'medium': 35,
        'low': 20,
        'very_low': 0 # Inclusive lower bound
    })
    
    # Vægtninger for risikokategorier
    risk_category_weights: Dict[str, float] = field(default_factory=lambda: {
        'financial_risk': 0.4,
        'business_risk': 0.3,
        'market_risk': 0.2,
        'liquidity_risk': 0.1
    })

    # Basispoint for virksomhedstyper (kan udvides)
    # Dette er en forenkling; i praksis kan det være en mere kompleks struktur
    # risk_base_scores: Dict[str, float] = field(default_factory=lambda: {...})

# Tilføj dette til __init__ af ComprehensiveValuationEngine:
# self.config = config or ValuationConfig()