# core/valuation/wacc_calculator.py
"""Modul til beregning af Weighted Average Cost of Capital (WACC)."""

import logging
from dataclasses import dataclass
from typing import Dict, Optional
# Brug den nye safe_numeric fra api_client
from ..data.client import safe_numeric
# Importer enums og profiler fra risk_assessment, hvis de er flyttet dertil
# from .risk_assessment import CompanyProfile, CompanyType # Juster sti hvis nødvendigt

# Hvis CompanyProfile og CompanyType stadig er i valuation_engine.py, importer dem derfra
# Eller flyt dem også til separate filer, f.eks. core/valuation/company_profile.py

# Midlertidig definition for kompabilitet - overvej at flytte til en fælles fil
from enum import Enum
class CompanyType(Enum):
    STARTUP = "startup"
    GROWTH = "growth"
    MATURE = "mature"
    CYCLICAL = "cyclical"
    UTILITY = "utility"
    BANK = "bank"
    REIT = "reit"

@dataclass
class CompanyProfile:
    ticker: str
    company_type: CompanyType
    sector: str
    industry: str
    market_cap: float
    revenue_growth_5y: float
    profit_margin: float
    debt_to_equity: float
    dividend_yield: float
    beta: float

logger = logging.getLogger(__name__)

@dataclass
class WACCInputs:
    """Centralized WACC configuration"""
    risk_free_rate: float = 0.04
    market_premium: float = 0.06 # Market Risk Premium (Rm - Rf)
    beta: float = 1.0
    tax_rate: float = 0.25
    debt_to_equity: float = 0.5
    cost_of_debt: float = 0.05
    # Enhanced factors - Inputs
    # Note: Size premium is now primarily calculated from market_cap, but this input is kept
    # for potential override or future use.
    size_premium: float = 0.0 
    country_risk_premium: float = 0.0
    liquidity_premium: float = 0.0

class WACCCalculator:
    """Advanced WACC calculation with multiple risk adjustments"""

    @staticmethod
    def _calculate_risk_adjustments(company_profile: CompanyProfile, inputs: WACCInputs) -> Dict[str, float]:
        """Calculate company-specific risk adjustments"""
        adjustments = {
            'liquidity_premium': 0.0,
            'size_premium': 0.0, # Calculated based on market cap
            'financial_distress': 0.0,
            'business_risk': 0.0,
            'total_adjustment': 0.0
        }
        
        # Size premium (smaller companies = higher risk)
        # This overrides the static inputs.size_premium for calculation
        if company_profile.market_cap < 1e9:  # < $1B
            adjustments['size_premium'] = 0.02
        elif company_profile.market_cap < 5e9:  # < $5B
            adjustments['size_premium'] = 0.01
            
        # Liquidity premium based on trading volume (assuming it's in inputs)
        # If this needs calculation, logic can be added here similar to size premium
        adjustments['liquidity_premium'] = inputs.liquidity_premium 
        
        # Financial distress premium
        if company_profile.debt_to_equity > 2.0:
            adjustments['financial_distress'] = 0.015
        elif company_profile.debt_to_equity > 1.0:
            adjustments['financial_distress'] = 0.005
            
        # Business risk premium by company type
        type_risk_premiums = {
            CompanyType.STARTUP: 0.03,
            CompanyType.GROWTH: 0.01,
            CompanyType.CYCLICAL: 0.015,
            CompanyType.MATURE: 0.0,
            CompanyType.UTILITY: -0.01, # Lower risk
            CompanyType.BANK: 0.005,
            CompanyType.REIT: 0.005
        }
        adjustments['business_risk'] = type_risk_premiums.get(company_profile.company_type, 0.0)
        
        # Total adjustment (sum of all calculated adjustments)
        adjustments['total_adjustment'] = sum(adjustments[key] for key in adjustments if key != 'total_adjustment')
        return adjustments

    @staticmethod
    def calculate_comprehensive_wacc(inputs: WACCInputs, company_profile: CompanyProfile) -> Dict[str, float]:
        """Calculate WACC with company-specific risk adjustments"""
        try:
            # --- Cost of Equity Calculation ---
            # 1. Base CAPM: Risk-Free Rate + Beta * Market Risk Premium
            base_cost_of_equity = inputs.risk_free_rate + inputs.beta * inputs.market_premium
            
            # 2. Risk adjustments based on company profile
            risk_adjustments = WACCCalculator._calculate_risk_adjustments(company_profile, inputs)
            
            # 3. Add other risk premiums (e.g., Country Risk Premium) separately
            #    These are typically added directly, not multiplied by beta.
            #    Using the inputs.country_risk_premium as provided.
            adjusted_cost_of_equity = (
                base_cost_of_equity +
                risk_adjustments['total_adjustment'] + # Includes calculated size premium
                inputs.country_risk_premium # Add country risk premium separately
                # Note: If inputs.size_premium was meant to be used instead of calculated one,
                # it would be added here, but we prioritize the calculated one.
                # + inputs.size_premium 
            )
            
            # --- Capital Structure Weights ---
            if inputs.debt_to_equity <= 0:
                debt_weight = 0.0
                equity_weight = 1.0
            else:
                # D/E ratio = D / E => D = D/E * E
                # V = D + E => V = (D/E * E) + E => V = E * (D/E + 1)
                # Weight of Debt = D / V = (D/E * E) / (E * (D/E + 1)) = D/E / (D/E + 1)
                debt_weight = inputs.debt_to_equity / (1 + inputs.debt_to_equity)
                equity_weight = 1.0 - debt_weight # Or E / V = 1 / (D/E + 1)
                
            # --- After-Tax Cost of Debt ---
            after_tax_cost_of_debt = inputs.cost_of_debt * (1 - inputs.tax_rate)
            
            # --- Final WACC Calculation ---
            # WACC = (E/V) * Re + (D/V) * Rd * (1 - Tc)
            wacc = (equity_weight * adjusted_cost_of_equity) + (debt_weight * after_tax_cost_of_debt)
            
            # --- Sanity Checks ---
            MIN_WACC, MAX_WACC = 0.02, 0.25
            if not (MIN_WACC <= wacc <= MAX_WACC):
                logger.warning(f"WACC ({wacc:.2%}) outside expected range ({MIN_WACC:.0%}-{MAX_WACC:.0%}). Capping/setting to bounds.")
                wacc = max(MIN_WACC, min(wacc, MAX_WACC)) # Clamp between 2% and 25%
                
            return {
                'wacc': wacc,
                'cost_of_equity': adjusted_cost_of_equity,
                'cost_of_debt': inputs.cost_of_debt,
                'after_tax_cost_of_debt': after_tax_cost_of_debt,
                'debt_weight': debt_weight,
                'equity_weight': equity_weight,
                'risk_adjustments': risk_adjustments,
                'beta_levered': inputs.beta,
                # Note: Tax shield value is part of WACC calculation (D/V * Rd * Tc)
                # This separate calculation might be redundant but kept for completeness.
                'tax_shield_value': debt_weight * inputs.cost_of_debt * inputs.tax_rate 
            }
        except Exception as e:
            logger.error(f"WACC calculation error: {e}")
            # Return conservative default
            return {
                'wacc': 0.12,
                'cost_of_equity': 0.12,
                'cost_of_debt': 0.06,
                'after_tax_cost_of_debt': 0.06 * (1 - 0.25),
                'debt_weight': 0.3,
                'equity_weight': 0.7,
                'risk_adjustments': {},
                'beta_levered': 1.0,
                'tax_shield_value': 0.3 * 0.06 * 0.25 # D/V * Rd * Tc
            }
