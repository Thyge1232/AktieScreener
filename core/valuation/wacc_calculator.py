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
    market_premium: float = 0.06
    beta: float = 1.0
    tax_rate: float = 0.25
    debt_to_equity: float = 0.5
    cost_of_debt: float = 0.05
    # Enhanced factors
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
            'size_premium': 0.0,
            'financial_distress': 0.0,
            'business_risk': 0.0,
            'total_adjustment': 0.0
        }
        # Size premium (smaller companies = higher risk)
        if company_profile.market_cap < 1e9:  # < $1B
            adjustments['size_premium'] = 0.02
        elif company_profile.market_cap < 5e9:  # < $5B
            adjustments['size_premium'] = 0.01
            
        # Liquidity premium based on trading volume (assuming it's in inputs)
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
            CompanyType.UTILITY: -0.01,
            CompanyType.BANK: 0.005,
            CompanyType.REIT: 0.005
        }
        adjustments['business_risk'] = type_risk_premiums.get(company_profile.company_type, 0.0)
        
        # Total adjustment
        adjustments['total_adjustment'] = sum(adjustments[key] for key in adjustments if key != 'total_adjustment')
        return adjustments

    @staticmethod
    def calculate_comprehensive_wacc(inputs: WACCInputs, company_profile: CompanyProfile) -> Dict[str, float]:
        """Calculate WACC with company-specific risk adjustments"""
        try:
            # Base cost of equity (CAPM)
            risk_premium = inputs.market_premium + inputs.size_premium + inputs.country_risk_premium
            base_cost_of_equity = inputs.risk_free_rate + inputs.beta * risk_premium
            
            # Risk adjustments based on company profile
            risk_adjustments = WACCCalculator._calculate_risk_adjustments(company_profile, inputs)
            adjusted_cost_of_equity = base_cost_of_equity + risk_adjustments['total_adjustment']
            
            # Capital structure weights
            if inputs.debt_to_equity <= 0:
                debt_weight = 0.0
                equity_weight = 1.0
            else:
                debt_weight = inputs.debt_to_equity / (1 + inputs.debt_to_equity)
                equity_weight = 1.0 - debt_weight
                
            # Tax shield on debt
            after_tax_cost_of_debt = inputs.cost_of_debt * (1 - inputs.tax_rate)
            
            # Final WACC calculation
            wacc = (equity_weight * adjusted_cost_of_equity) + (debt_weight * after_tax_cost_of_debt)
            
            # Sanity checks
            if wacc < 0.02:  # Less than 2%
                logger.warning(f"Unusually low WACC ({wacc:.1%}), setting minimum of 3%")
                wacc = 0.03
            elif wacc > 0.25:  # More than 25%
                logger.warning(f"Unusually high WACC ({wacc:.1%}), capping at 20%")
                wacc = 0.20
                
            return {
                'wacc': wacc,
                'cost_of_equity': adjusted_cost_of_equity,
                'cost_of_debt': inputs.cost_of_debt,
                'after_tax_cost_of_debt': after_tax_cost_of_debt,
                'debt_weight': debt_weight,
                'equity_weight': equity_weight,
                'risk_adjustments': risk_adjustments,
                'beta_levered': inputs.beta,
                'tax_shield_value': debt_weight * after_tax_cost_of_debt * inputs.tax_rate
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
                'tax_shield_value': 0.3 * 0.06 * (1 - 0.25) * 0.25
            }
