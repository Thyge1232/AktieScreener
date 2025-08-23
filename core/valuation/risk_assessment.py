# core/valuation/risk_assessment.py
"""Modul til risikovurdering af virksomheder."""

import logging
from dataclasses import dataclass # Tilføjer denne
from typing import Optional # Tilføjer denne
from typing import Dict, List, Any
from .dcf_engine import ValuationInputs # Bruges til input
# Antager CompanyProfile og RiskLevel findes i en fÃ¦lles fil eller flyttes hertil
# from .valuation_engine import CompanyProfile, RiskLevel, CompanyType

logger = logging.getLogger(__name__)

# Midlertidige definitioner - flyt til en fÃ¦lles fil
from enum import Enum
class RiskLevel(Enum):
    """Risk assessment levels"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class CompanyType(Enum):
    """Enhanced company classification"""
    STARTUP = "startup"
    GROWTH = "growth"
    MATURE = "mature"
    CYCLICAL = "cyclical"
    ASSET_HEAVY = "asset_heavy"
    BANK = "bank"
    REIT = "reit"
    UTILITY = "utility"
    COMMODITY = "commodity"

@dataclass
class CompanyProfile:
    """Enhanced company profile with risk assessment - Moved from valuation_engine.py"""
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
    risk_level: RiskLevel = RiskLevel.MEDIUM
    esg_score: Optional[float] = None
    competitive_moat: str = "none"  # none, narrow, wide

class RiskAssessment:
    """Comprehensive risk assessment framework"""
    RISK_FACTORS = {
        'financial': ['high_debt', 'low_liquidity', 'declining_margins', 'negative_fcf'],
        'operational': ['single_product', 'regulatory_risk', 'competition', 'technology_disruption'],
        'market': ['cyclical_industry', 'concentration_risk', 'currency_exposure'],
        'management': ['governance_issues', 'key_person_risk', 'strategy_changes']
    }

    @classmethod
    def _assess_financial_risk(cls, inputs: ValuationInputs) -> float:
        """Assess financial risk (0-100)"""
        score = 0
        # Debt levels
        if inputs.debt_to_equity > 2.0:
            score += 25
        elif inputs.debt_to_equity > 1.0:
            score += 15
        elif inputs.debt_to_equity > 0.5:
            score += 5
        # Interest coverage
        if inputs.interest_coverage < 2.0:
            score += 25
        elif inputs.interest_coverage < 5.0:
            score += 10
        # Profitability
        if inputs.operating_margin < 0:
            score += 20
        elif inputs.operating_margin < 0.05:
            score += 10
        # Free cash flow
        if inputs.free_cash_flow <= 0:
            score += 20
        elif inputs.free_cash_flow < inputs.capex:
            score += 10
        return min(score, 100)

    @classmethod
    def _assess_business_risk(cls, profile: CompanyProfile) -> float:
        """Assess business/operational risk"""
        base_scores = {
            CompanyType.STARTUP: 60,
            CompanyType.GROWTH: 40,
            CompanyType.CYCLICAL: 50,
            CompanyType.MATURE: 20,
            CompanyType.UTILITY: 15,
            CompanyType.BANK: 35,
            CompanyType.REIT: 25
        }
        score = base_scores.get(profile.company_type, 30)
        # Beta adjustment
        if profile.beta > 1.5:
            score += 15
        elif profile.beta > 1.2:
            score += 10
        elif profile.beta < 0.8:
            score -= 5
        return min(score, 100)

    @classmethod
    def _assess_market_risk(cls, profile: CompanyProfile) -> float:
        """Assess market-related risks"""
        score = 30  # Base market risk
        # Market cap size risk
        if profile.market_cap < 1e9:
            score += 20
        elif profile.market_cap < 10e9:
            score += 10
        # Sector-specific risks
        high_risk_sectors = ['technology', 'biotech', 'mining', 'oil']
        if any(sector in profile.sector.lower() for sector in high_risk_sectors):
            score += 15
        return min(score, 100)

    @classmethod
    def _assess_liquidity_risk(cls, inputs: ValuationInputs) -> float:
        """Assess liquidity risk"""
        score = 0
        # Cash position
        cash_ratio = inputs.cash_and_equivalents / max(inputs.total_debt, inputs.revenue * 0.1)
        if cash_ratio < 0.1:
            score += 30
        elif cash_ratio < 0.3:
            score += 15
        # Working capital
        if inputs.working_capital < 0:
            score += 25
        return min(score, 100)

    @classmethod
    def _identify_key_risks(cls, risk_scores: Dict, inputs: ValuationInputs, profile: CompanyProfile) -> List[str]:
        """Identify top risk factors"""
        risks = []
        if risk_scores['financial_risk'] > 50:
            if inputs.debt_to_equity > 1.5:
                risks.append("High debt levels relative to equity")
            if inputs.interest_coverage < 3.0:
                risks.append("Low interest coverage ratio")
            if inputs.free_cash_flow <= 0:
                risks.append("Negative or zero free cash flow")
        if risk_scores['business_risk'] > 60:
            risks.append(f"High business risk due to {profile.company_type.value} nature")
            if profile.beta > 1.5:
                risks.append("High stock price volatility")
        if risk_scores['market_risk'] > 50:
            if profile.market_cap < 1e9:
                risks.append("Small company size increases volatility")
        return risks[:5]  # Top 5 risks

    @classmethod
    def _suggest_risk_mitigations(cls, risk_scores: Dict) -> List[str]:
        """Suggest risk mitigation strategies"""
        mitigations = []
        if risk_scores['financial_risk'] > 40:
            mitigations.append("Monitor debt levels and cash flow trends closely")
            mitigations.append("Consider position sizing based on financial strength")
        if risk_scores['business_risk'] > 50:
            mitigations.append("Diversify across different business models")
            mitigations.append("Monitor competitive positioning regularly")
        if risk_scores['market_risk'] > 60:
            mitigations.append("Consider hedging strategies for market exposure")
        return mitigations

    @classmethod
    def assess_company_risk(cls, inputs: ValuationInputs, profile: CompanyProfile) -> Dict[str, Any]:
        """Comprehensive risk assessment"""
        risk_scores = {
            'financial_risk': cls._assess_financial_risk(inputs),
            'business_risk': cls._assess_business_risk(profile),
            'market_risk': cls._assess_market_risk(profile),
            'liquidity_risk': cls._assess_liquidity_risk(inputs)
        }
        # Overall risk score (0-100, higher = riskier)
        weights = {'financial_risk': 0.4, 'business_risk': 0.3, 'market_risk': 0.2, 'liquidity_risk': 0.1}
        overall_risk = sum(score * weights[category] for category, score in risk_scores.items())
        # Risk level classification
        if overall_risk < 20:
            risk_level = RiskLevel.VERY_LOW
        elif overall_risk < 35:
            risk_level = RiskLevel.LOW
        elif overall_risk < 55:
            risk_level = RiskLevel.MEDIUM
        elif overall_risk < 75:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.VERY_HIGH
        return {
            'overall_risk_score': overall_risk,
            'risk_level': risk_level,
            'risk_breakdown': risk_scores,
            'key_risk_factors': cls._identify_key_risks(risk_scores, inputs, profile),
            'risk_mitigation_suggestions': cls._suggest_risk_mitigations(risk_scores)
        }
