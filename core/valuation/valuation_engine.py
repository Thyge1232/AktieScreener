# core/valuation/valuation_engine.py - Komplet og Forbedret Version
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from enum import Enum
import streamlit as st # Bruges stadig for UI callbacks, men ikke i beregningslogik
import time
import logging
from datetime import datetime
import warnings
from scipy import stats
import math

# Import API client
from core.data.api_client import get_fundamental_data, get_live_price, APIResponse

# Setup logging
logger = logging.getLogger(__name__)

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

class ValuationMethod(Enum):
    """Available valuation methods"""
    DCF = "dcf"
    COMPARABLE_PE = "comparable_pe"
    COMPARABLE_EV_EBITDA = "comparable_ev_ebitda"
    PRICE_TO_BOOK = "price_to_book"
    PRICE_TO_SALES = "price_to_sales"
    DIVIDEND_DISCOUNT = "dividend_discount"
    ASSET_BASED = "asset_based"
    SUM_OF_PARTS = "sum_of_parts"

class RiskLevel(Enum):
    """Risk assessment levels"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    VERY_HIGH = "very_high"

@dataclass
class CompanyProfile:
    """Enhanced company profile with risk assessment"""
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

@dataclass
class ValuationInputs:
    """Comprehensive valuation inputs with validation"""
    # Core financials
    revenue: float
    ebitda: float
    net_income: float
    free_cash_flow: float
    book_value: float
    dividend_per_share: float
    shares_outstanding: float
    
    # Growth and profitability
    revenue_growth_rate: float
    ebitda_growth_rate: float
    terminal_growth_rate: float
    operating_margin: float
    tax_rate: float
    
    # Balance sheet
    total_debt: float
    cash_and_equivalents: float
    working_capital: float
    capex: float
    
    # Risk metrics
    beta: float
    debt_to_equity: float
    interest_coverage: float
    
    # Industry benchmarks
    industry_pe: float = 15.0
    industry_ev_ebitda: float = 10.0
    industry_growth_rate: float = 0.05
    
    def __post_init__(self):
        """Validate and normalize inputs after creation"""
        self._validate_inputs()
        self._normalize_growth_rates()
    
    def _validate_inputs(self):
        """Validate financial inputs for consistency"""
        errors = []
        
        # Basic validation
        if self.shares_outstanding <= 0:
            errors.append("Shares outstanding must be positive")
        
        if self.revenue <= 0:
            errors.append("Revenue must be positive")
        
        # Cross-validation
        if self.ebitda > self.revenue:
            logger.warning(f"EBITDA ({self.ebitda:.0f}) exceeds Revenue ({self.revenue:.0f})")
        
        if abs(self.net_income) > self.revenue * 2:  # Extreme profit/loss
            logger.warning(f"Net income ({self.net_income:.0f}) seems extreme vs Revenue ({self.revenue:.0f})")
        
        if errors:
            raise ValueError(f"Validation errors: {'; '.join(errors)}")
    
    def _normalize_growth_rates(self):
        """Apply realistic bounds to growth rates"""
        # Cap extreme growth rates
        self.revenue_growth_rate = max(-0.50, min(self.revenue_growth_rate, 1.00))  # -50% to 100%
        self.ebitda_growth_rate = max(-0.75, min(self.ebitda_growth_rate, 1.50))   # -75% to 150%
        self.terminal_growth_rate = max(0.00, min(self.terminal_growth_rate, 0.05)) # 0% to 5%
        
        # Log adjustments
        original_rates = (self.revenue_growth_rate, self.ebitda_growth_rate, self.terminal_growth_rate)
        if any(rate != orig for rate, orig in zip([self.revenue_growth_rate, self.ebitda_growth_rate, self.terminal_growth_rate], original_rates)):
            logger.info("Growth rates normalized to realistic bounds")

@dataclass 
class WACCInputs:
    """Weighted Average Cost of Capital inputs with market context"""
    risk_free_rate: float
    market_premium: float
    beta: float
    tax_rate: float
    debt_to_equity: float
    cost_of_debt: float
    
    # Enhanced factors
    size_premium: float = 0.0  # Small company premium
    country_risk_premium: float = 0.0
    liquidity_premium: float = 0.0
    
    def __post_init__(self):
        """Validate WACC inputs"""
        if self.risk_free_rate < 0 or self.risk_free_rate > 0.20:
            raise ValueError(f"Risk-free rate {self.risk_free_rate:.1%} seems unrealistic")
        
        if self.market_premium < 0 or self.market_premium > 0.15:
            raise ValueError(f"Market premium {self.market_premium:.1%} seems unrealistic")

@dataclass
class ValuationResult:
    """Comprehensive valuation result with confidence metrics"""
    method: ValuationMethod
    fair_value: float
    confidence_level: float  # 0-1 scale
    key_assumptions: Dict[str, float]
    sensitivity_analysis: Dict[str, Tuple[float, float]]  # (downside, upside)
    risk_factors: List[str]
    upside_scenarios: Dict[str, float]
    downside_scenarios: Dict[str, float]

def safe_numeric(value: Any, default: float = 0.0, min_val: float = None, max_val: float = None) -> float:
    """Enhanced numeric conversion with bounds checking"""
    try:
        if pd.isna(value) or value is None or value == '' or value == 'None':
            return default
        
        if isinstance(value, str):
            # Handle percentage strings
            if value.endswith('%'):
                numeric_val = float(value[:-1]) / 100
            else:
                # Clean common formatting
                cleaned = value.replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
                numeric_val = float(cleaned)
        else:
            numeric_val = float(value)
        
        # Apply bounds if specified
        if min_val is not None:
            numeric_val = max(numeric_val, min_val)
        if max_val is not None:
            numeric_val = min(numeric_val, max_val)
        
        # Check for extreme values
        if abs(numeric_val) > 1e15:  # Very large numbers
            logger.warning(f"Extreme numeric value encountered: {numeric_val}")
            return default
        
        return numeric_val
        
    except (ValueError, TypeError) as e:
        logger.debug(f"Numeric conversion failed for {value}: {e}")
        return default

class IntelligentCompanyClassifier:
    """AI-like company classification based on financial characteristics"""
    
    CLASSIFICATION_RULES = {
        CompanyType.BANK: {
            'sector_keywords': ['financial', 'bank', 'insurance'],
            'financial_ratios': {
                'interest_income_ratio': (0.5, float('inf')),  # High interest income
                'loan_to_deposit': (0.3, 2.0)
            }
        },
        
        CompanyType.REIT: {
            'sector_keywords': ['reit', 'real estate'],
            'financial_ratios': {
                'dividend_yield': (0.03, 0.12),  # 3-12% dividend yield
                'debt_to_equity': (0.5, 3.0)    # REITs typically levered
            }
        },
        
        CompanyType.UTILITY: {
            'sector_keywords': ['utilities', 'electric', 'gas', 'water'],
            'financial_ratios': {
                'dividend_yield': (0.025, 0.08),  # Stable dividends
                'beta': (0.3, 0.8),               # Low volatility
                'debt_to_equity': (0.4, 1.5)     # Infrastructure debt
            }
        },
        
        CompanyType.STARTUP: {
            'financial_ratios': {
                'pe_ratio': (30, float('inf')),   # High P/E
                'revenue_growth': (0.20, float('inf')),  # >20% growth
                'dividend_yield': (0, 0.02),     # Low/no dividends
                'market_cap': (0, 10e9)          # Smaller companies
            }
        },
        
        CompanyType.GROWTH: {
            'financial_ratios': {
                'pe_ratio': (20, 50),
                'revenue_growth': (0.10, 0.30),  # 10-30% growth
                'profit_margin': (0.05, 0.25),
                'dividend_yield': (0, 0.03)
            }
        },
        
        CompanyType.MATURE: {
            'financial_ratios': {
                'pe_ratio': (8, 25),
                'revenue_growth': (0, 0.15),     # Slower growth
                'dividend_yield': (0.02, 0.08),  # Regular dividends
                'market_cap': (1e9, float('inf'))  # Established companies
            }
        },
        
        CompanyType.CYCLICAL: {
            'sector_keywords': ['materials', 'energy', 'industrials', 'mining'],
            'financial_ratios': {
                'beta': (1.2, 2.5),              # High volatility
                'debt_to_equity': (0.3, 2.0),
                'operating_margin_volatility': (0.05, float('inf'))
            }
        }
    }
    
    @classmethod
    def classify_company(cls, fundamental_data: Dict, sector: str = "") -> Tuple[CompanyType, float]:
        """Classify company type with confidence score"""
        
        # Extract key metrics
        metrics = {
            'pe_ratio': safe_numeric(fundamental_data.get('PERatio'), 15),
            'market_cap': safe_numeric(fundamental_data.get('MarketCapitalization'), 1e9),
            'dividend_yield': safe_numeric(fundamental_data.get('DividendYield'), 0),
            'beta': safe_numeric(fundamental_data.get('Beta'), 1.0),
            'debt_to_equity': safe_numeric(fundamental_data.get('DebtToEquity'), 0.5),
            'revenue_growth': safe_numeric(fundamental_data.get('QuarterlyRevenueGrowthYOY'), 0.05),
            'profit_margin': safe_numeric(fundamental_data.get('ProfitMargin'), 0.05),
            'operating_margin': safe_numeric(fundamental_data.get('OperatingMarginTTM'), 0.08)
        }
        
        sector_lower = sector.lower()
        best_match = CompanyType.MATURE
        highest_score = 0.0
        
        for company_type, rules in cls.CLASSIFICATION_RULES.items():
            score = 0.0
            matches = 0
            total_checks = 0
            
            # Check sector keywords
            if 'sector_keywords' in rules:
                total_checks += 1
                if any(keyword in sector_lower for keyword in rules['sector_keywords']):
                    score += 0.4  # High weight for sector match
                    matches += 1
            
            # Check financial ratios
            if 'financial_ratios' in rules:
                for ratio_name, (min_val, max_val) in rules['financial_ratios'].items():
                    total_checks += 1
                    metric_value = metrics.get(ratio_name, 0)
                    
                    if min_val <= metric_value <= max_val:
                        score += 0.6 / len(rules['financial_ratios'])  # Weighted by number of ratios
                        matches += 1
            
            # Calculate confidence as percentage of matching criteria
            confidence = matches / max(total_checks, 1)
            
            if confidence > highest_score:
                highest_score = confidence
                best_match = company_type
        
        return best_match, min(highest_score, 0.95)  # Cap confidence at 95%

class WACCCalculator:
    """Advanced WACC calculation with multiple risk adjustments"""
    
    @staticmethod
    def _calculate_risk_adjustments(profile: CompanyProfile, inputs: WACCInputs) -> Dict[str, float]:
        """Calculate company-specific risk adjustments"""
        adjustments = {
            'liquidity_premium': 0.0,
            'size_premium': 0.0,
            'financial_distress': 0.0,
            'business_risk': 0.0,
            'total_adjustment': 0.0
        }
        
        # Size premium (smaller companies = higher risk)
        if profile.market_cap < 1e9:  # < $1B
            adjustments['size_premium'] = 0.02
        elif profile.market_cap < 5e9:  # < $5B
            adjustments['size_premium'] = 0.01
            
        # Liquidity premium based on trading volume (assuming it's in inputs)
        adjustments['liquidity_premium'] = inputs.liquidity_premium
        
        # Financial distress premium
        if profile.debt_to_equity > 2.0:
            adjustments['financial_distress'] = 0.015
        elif profile.debt_to_equity > 1.0:
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
        adjustments['business_risk'] = type_risk_premiums.get(profile.company_type, 0.0)
        
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
                'after_tax_cost_of_debt': 0.06 * (1 - 0.25), # Assuming 25% tax rate
                'debt_weight': 0.3,
                'equity_weight': 0.7,
                'risk_adjustments': {},
                'beta_levered': 1.0,
                'tax_shield_value': 0.3 * 0.06 * (1 - 0.25) * 0.25
            }

class EnhancedDCFValuation:
    """Sophisticated DCF model with multiple scenarios and sensitivity analysis"""
    
    @staticmethod
    def _validate_dcf_inputs(inputs: ValuationInputs) -> ValuationInputs:
        """Validate and enhance DCF inputs"""
        validated = inputs
        # Ensure positive FCF - estimate if needed
        if validated.free_cash_flow <= 0:
            if validated.ebitda > 0:
                # FCF = EBITDA - Tax - CapEx - Change in Working Capital
                estimated_tax = validated.ebitda * validated.tax_rate
                estimated_fcf = validated.ebitda - estimated_tax - validated.capex
                validated.free_cash_flow = max(estimated_fcf, validated.net_income * 0.6)
            elif validated.net_income > 0:
                validated.free_cash_flow = validated.net_income * 0.7  # Conservative estimate
            else:
                # Last resort - estimate from revenue
                validated.free_cash_flow = validated.revenue * 0.03
        
        # Validate terminal growth rate
        if validated.terminal_growth_rate >= validated.revenue_growth_rate * 0.8:
            validated.terminal_growth_rate = max(0.02, validated.revenue_growth_rate * 0.3)
            
        return validated

    @staticmethod
    def _create_growth_stages(inputs: ValuationInputs, projection_years: int) -> List[Dict]:
        """Create multi-stage growth model"""
        stages = []
        # Stage 1: High growth (years 1-5)
        high_growth_years = min(5, projection_years // 2)
        for year in range(high_growth_years):
            # Fade growth over time
            fade_factor = 0.85 ** year  # 15% annual fade
            growth_rate = inputs.revenue_growth_rate * fade_factor
            stages.append({
                'stage': 'high_growth',
                'growth_rate': growth_rate,
                'description': f'High growth period - year {year + 1}'
            })
        
        # Stage 2: Transitional growth (years 6-8)
        transition_years = min(3, projection_years - high_growth_years)
        transition_start = inputs.revenue_growth_rate * (0.85 ** high_growth_years)
        transition_end = inputs.terminal_growth_rate
        for year in range(transition_years):
            # Linear interpolation between transition start and terminal
            progress = year / max(transition_years - 1, 1)
            growth_rate = transition_start * (1 - progress) + transition_end * progress
            stages.append({
                'stage': 'transition',
                'growth_rate': growth_rate,
                'description': f'Transition period - year {high_growth_years + year + 1}'
            })
        
        # Stage 3: Mature growth (remaining years)
        remaining_years = projection_years - len(stages)
        for year in range(remaining_years):
            stages.append({
                'stage': 'mature',
                'growth_rate': inputs.terminal_growth_rate,
                'description': f'Mature growth - year {len(stages) + year + 1}'
            })
        
        return stages

    @staticmethod
    def _perform_sensitivity_analysis(inputs: ValuationInputs, base_wacc: float, 
                                    projection_years: int) -> Dict[str, Dict[str, float]]:
        """Perform sensitivity analysis on key variables"""
        # Base case value
        base_result = EnhancedDCFValuation.calculate_comprehensive_dcf(
            inputs, {'wacc': base_wacc}, projection_years
        )
        base_value = base_result['value_per_share']
        sensitivity = {}
        
        # WACC sensitivity
        wacc_scenarios = {
            'low_wacc': base_wacc * 0.8,
            'high_wacc': base_wacc * 1.2
        }
        sensitivity['wacc'] = {}
        for scenario, wacc in wacc_scenarios.items():
            try:
                result = EnhancedDCFValuation.calculate_comprehensive_dcf(
                    inputs, {'wacc': wacc}, projection_years
                )
                sensitivity['wacc'][scenario] = result['value_per_share']
            except:
                sensitivity['wacc'][scenario] = base_value
                
        # Growth rate sensitivity
        growth_scenarios = {
            'low_growth': inputs.revenue_growth_rate * 0.7,
            'high_growth': inputs.revenue_growth_rate * 1.3
        }
        sensitivity['growth_rate'] = {}
        for scenario, growth in growth_scenarios.items():
            try:
                # Create a copy of inputs to modify
                modified_inputs = ValuationInputs(**inputs.__dict__)
                modified_inputs.revenue_growth_rate = growth
                result = EnhancedDCFValuation.calculate_comprehensive_dcf(
                    modified_inputs, {'wacc': base_wacc}, projection_years
                )
                sensitivity['growth_rate'][scenario] = result['value_per_share']
            except:
                sensitivity['growth_rate'][scenario] = base_value
                
        return sensitivity

    @staticmethod
    def _monte_carlo_simulation(inputs: ValuationInputs, wacc_result: Dict, 
                              projection_years: int, num_simulations: int = 100) -> Dict[str, float]: # Reduced for performance
        """Monte Carlo simulation for confidence intervals"""
        try:
            values = []
            base_wacc = wacc_result['wacc']
            for _ in range(min(num_simulations, 100)):  # Limit for performance
                # Randomly vary key parameters
                wacc_variation = np.random.normal(0, 0.01)  # 1% std dev
                growth_variation = np.random.normal(0, 0.02)  # 2% std dev
                
                # Create scenario inputs
                # Create a copy of inputs to modify
                scenario_inputs = ValuationInputs(**inputs.__dict__)
                scenario_inputs.revenue_growth_rate = max(0, inputs.revenue_growth_rate + growth_variation)
                scenario_wacc = max(0.02, base_wacc + wacc_variation)
                
                try:
                    result = EnhancedDCFValuation.calculate_comprehensive_dcf(
                        scenario_inputs, {'wacc': scenario_wacc}, projection_years
                    )
                    values.append(result['value_per_share'])
                except:
                    continue
                    
            if len(values) > 10:  # Enough simulations for statistics
                values = np.array(values)
                return {
                    'p10': float(np.percentile(values, 10)),
                    'p25': float(np.percentile(values, 25)),
                    'p50': float(np.percentile(values, 50)),
                    'p75': float(np.percentile(values, 75)),
                    'p90': float(np.percentile(values, 90)),
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values))
                }
        except Exception as e:
            logger.warning(f"Monte Carlo simulation failed: {e}")
            
        # Fallback - simple confidence intervals
        base_value = inputs.free_cash_flow / inputs.shares_outstanding * 15  # Simple multiple
        return {
            'p10': base_value * 0.6,
            'p25': base_value * 0.8,
            'p50': base_value,
            'p75': base_value * 1.2,
            'p90': base_value * 1.4,
            'mean': base_value,
            'std': base_value * 0.2
        }

    @staticmethod
    def _fallback_dcf_result(inputs: ValuationInputs) -> Dict[str, Any]:
        """Fallback DCF result when calculation fails"""
        estimated_value = (inputs.free_cash_flow * 15) / inputs.shares_outstanding
        return {
            'enterprise_value': inputs.free_cash_flow * 15,
            'equity_value': inputs.free_cash_flow * 15,
            'value_per_share': estimated_value,
            'terminal_value': inputs.free_cash_flow * 12,
            'pv_terminal': inputs.free_cash_flow * 10,
            'pv_explicit_period': inputs.free_cash_flow * 5,
            'terminal_value_percentage': 0.67,
            'projected_fcf': [],
            'growth_stages': [],
            'sensitivity_analysis': {},
            'confidence_intervals': {
                'p50': estimated_value,
                'p10': estimated_value * 0.7,
                'p90': estimated_value * 1.3
            },
            'assumptions': {'note': 'Fallback calculation used'}
        }

    @staticmethod
    def calculate_comprehensive_dcf(inputs: ValuationInputs, wacc_result: Dict, 
                                  projection_years: int = 10) -> Dict[str, Any]:
        """Calculate DCF with enhanced modeling and sensitivity analysis"""
        try:
            # Validate and adjust inputs
            validated_inputs = EnhancedDCFValuation._validate_dcf_inputs(inputs)
            wacc = wacc_result['wacc']
            
            # Multi-stage growth model
            growth_stages = EnhancedDCFValuation._create_growth_stages(validated_inputs, projection_years)
            
            # Project cash flows for each stage
            projected_fcf = []
            cumulative_pv = 0
            current_fcf = validated_inputs.free_cash_flow
            
            for year, stage_info in enumerate(growth_stages, 1):
                # Apply growth rate with fade
                growth_rate = stage_info['growth_rate']
                current_fcf *= (1 + growth_rate)
                
                # Discount to present value
                pv_factor = 1 / ((1 + wacc) ** year)
                pv_fcf = current_fcf * pv_factor
                
                projected_fcf.append({
                    'year': year,
                    'fcf': current_fcf,
                    'growth_rate': growth_rate,
                    'pv_factor': pv_factor,
                    'pv_fcf': pv_fcf,
                    'stage': stage_info['stage']
                })
                cumulative_pv += pv_fcf
            
            # Terminal value calculation
            terminal_fcf = current_fcf * (1 + validated_inputs.terminal_growth_rate)
            terminal_multiple = 1 / (wacc - validated_inputs.terminal_growth_rate)
            terminal_value = terminal_fcf * terminal_multiple
            pv_terminal = terminal_value / ((1 + wacc) ** projection_years)
            
            # Enterprise and equity value
            enterprise_value = cumulative_pv + pv_terminal
            # Adjust for cash and debt
            net_debt = max(0, validated_inputs.total_debt - validated_inputs.cash_and_equivalents)
            equity_value = max(0, enterprise_value - net_debt)
            
            # Per share value
            value_per_share = equity_value / validated_inputs.shares_outstanding
            
            # Sensitivity analysis
            sensitivity = EnhancedDCFValuation._perform_sensitivity_analysis(
                validated_inputs, wacc, projection_years
            )
            
            # Monte Carlo simulation for confidence intervals
            confidence_intervals = EnhancedDCFValuation._monte_carlo_simulation(
                validated_inputs, wacc_result, projection_years
            )
            
            return {
                'enterprise_value': enterprise_value,
                'equity_value': equity_value,
                'value_per_share': value_per_share,
                'terminal_value': terminal_value,
                'pv_terminal': pv_terminal,
                'pv_explicit_period': cumulative_pv,
                'terminal_value_percentage': pv_terminal / enterprise_value if enterprise_value > 0 else 0,
                'projected_fcf': projected_fcf,
                'growth_stages': growth_stages,
                'sensitivity_analysis': sensitivity,
                'confidence_intervals': confidence_intervals,
                'assumptions': {
                    'wacc': wacc,
                    'terminal_growth': validated_inputs.terminal_growth_rate,
                    'projection_years': projection_years,
                    'initial_fcf': validated_inputs.free_cash_flow
                }
            }
        except Exception as e:
            logger.error(f"Enhanced DCF calculation failed: {e}")
            return EnhancedDCFValuation._fallback_dcf_result(inputs)

class ComparableValuation:
    """Industry comparable valuation methods"""
    
    @staticmethod
    def calculate_pe_valuation(inputs: ValuationInputs, industry_pe: float = None) -> Dict[str, float]:
        """P/E ratio based valuation"""
        try:
            target_pe = industry_pe or inputs.industry_pe
            # Adjust P/E for growth (PEG approach)
            if inputs.revenue_growth_rate > 0.05:  # Above 5% growth
                growth_adjustment = 1 + (inputs.revenue_growth_rate - 0.05) * 2  # 2x growth premium
                target_pe *= growth_adjustment
                
            # Calculate EPS
            eps = inputs.net_income / inputs.shares_outstanding
            fair_value = eps * target_pe
            return {
                'fair_value': max(0, fair_value),
                'target_pe': target_pe,
                'current_eps': eps,
                'method': 'P/E Comparable'
            }
        except Exception as e:
            logger.error(f"P/E valuation failed: {e}")
            return {'fair_value': 0, 'error': str(e)}

    @staticmethod
    def calculate_ev_ebitda_valuation(inputs: ValuationInputs, industry_ev_ebitda: float = None) -> Dict[str, float]:
        """EV/EBITDA based valuation"""
        try:
            target_multiple = industry_ev_ebitda or inputs.industry_ev_ebitda
            # Growth adjustment
            if inputs.ebitda_growth_rate > 0.05:
                growth_adjustment = 1 + (inputs.ebitda_growth_rate - 0.05) * 1.5
                target_multiple *= growth_adjustment
                
            # Calculate enterprise value
            enterprise_value = inputs.ebitda * target_multiple
            # Convert to equity value
            net_debt = inputs.total_debt - inputs.cash_and_equivalents
            equity_value = max(0, enterprise_value - net_debt)
            fair_value = equity_value / inputs.shares_outstanding
            return {
                'fair_value': fair_value,
                'enterprise_value': enterprise_value,
                'target_multiple': target_multiple,
                'method': 'EV/EBITDA Comparable'
            }
        except Exception as e:
            logger.error(f"EV/EBITDA valuation failed: {e}")
            return {'fair_value': 0, 'error': str(e)}

    @staticmethod
    def calculate_price_to_book(inputs: ValuationInputs, industry_pb: float = 2.0) -> Dict[str, float]:
        """Price-to-book valuation"""
        try:
            book_value_per_share = inputs.book_value / inputs.shares_outstanding
            # Adjust P/B for ROE
            roe = inputs.net_income / max(inputs.book_value, 1)
            if roe > 0.15:  # High ROE deserves premium
                pb_multiple = industry_pb * (1 + (roe - 0.15))
            else:
                pb_multiple = industry_pb
                
            fair_value = book_value_per_share * pb_multiple
            return {
                'fair_value': max(0, fair_value),
                'book_value_per_share': book_value_per_share,
                'pb_multiple': pb_multiple,
                'roe': roe,
                'method': 'Price-to-Book'
            }
        except Exception as e:
            logger.error(f"P/B valuation failed: {e}")
            return {'fair_value': 0, 'error': str(e)}

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

class ComprehensiveValuationEngine:
    """Main valuation engine orchestrating all methods"""
    
    def __init__(self):
        self.dcf_calculator = EnhancedDCFValuation()
        self.comparable_calculator = ComparableValuation()
        self.risk_assessor = RiskAssessment()
        self.wacc_calculator = WACCCalculator()

    def _create_valuation_inputs(self, data: Dict, profile: CompanyProfile) -> ValuationInputs:
        """Create comprehensive valuation inputs from fundamental data"""
        # Basic financials
        revenue = safe_numeric(data.get('RevenueTTM'), 1e9)
        ebitda = safe_numeric(data.get('EBITDA'), revenue * 0.15)
        net_income = safe_numeric(data.get('NetIncomeTTM'), revenue * 0.05)
        book_value = safe_numeric(data.get('BookValue'), 10) * safe_numeric(data.get('SharesOutstanding'), 1e6)
        dividend_per_share = safe_numeric(data.get('DividendPerShare'), 0)
        shares_outstanding = safe_numeric(data.get('SharesOutstanding'), 1e6)
        
        # Growth and profitability
        revenue_growth_rate = safe_numeric(data.get('QuarterlyRevenueGrowthYOY'), 0.05)
        # Estimate EBITDA growth (could be refined with more data)
        ebitda_growth_rate = revenue_growth_rate * 0.9 # Simplified assumption
        terminal_growth_rate = 0.025 # Default terminal growth
        operating_margin = safe_numeric(data.get('OperatingMarginTTM'), 0.08)
        tax_rate = 0.25 # Default tax rate, could be refined
        
        # Balance sheet
        total_debt = safe_numeric(data.get('TotalDebt'), revenue * 0.3) # Estimate if missing
        cash_and_equivalents = safe_numeric(data.get('CashAndCashEquivalents'), total_debt * 0.1) # Estimate if missing
        working_capital = safe_numeric(data.get('WorkingCapital'), revenue * 0.1) # Estimate if missing
        capex = safe_numeric(data.get('CapitalExpenditures'), revenue * 0.05) # Estimate if missing
        
        # Risk metrics
        beta = profile.beta
        debt_to_equity = profile.debt_to_equity
        # Estimate interest coverage (EBITDA / Interest Expense)
        # We don't have interest expense, so we estimate it
        estimated_interest_expense = total_debt * 0.05 # Assume 5% average interest rate
        interest_coverage = ebitda / max(estimated_interest_expense, 1)
        
        # Industry benchmarks (could be fetched from a separate source or config)
        industry_pe = 15.0
        industry_ev_ebitda = 10.0
        industry_growth_rate = 0.05
        
        return ValuationInputs(
            revenue=revenue,
            ebitda=ebitda,
            net_income=net_income,
            free_cash_flow=safe_numeric(data.get('OperatingCashflowTTM'), net_income * 0.7) - capex,
            book_value=book_value,
            dividend_per_share=dividend_per_share,
            shares_outstanding=shares_outstanding,
            revenue_growth_rate=revenue_growth_rate,
            ebitda_growth_rate=ebitda_growth_rate,
            terminal_growth_rate=terminal_growth_rate,
            operating_margin=operating_margin,
            tax_rate=tax_rate,
            total_debt=total_debt,
            cash_and_equivalents=cash_and_equivalents,
            working_capital=working_capital,
            capex=capex,
            beta=beta,
            debt_to_equity=debt_to_equity,
            interest_coverage=interest_coverage,
            industry_pe=industry_pe,
            industry_ev_ebitda=industry_ev_ebitda,
            industry_growth_rate=industry_growth_rate
        )

    def _create_wacc_inputs(self, profile: CompanyProfile, inputs: ValuationInputs) -> WACCInputs:
        """Create WACC inputs"""
        # Default market parameters (could be configurable)
        risk_free_rate = 0.04  # 4% risk-free rate
        market_premium = 0.06   # 6% market risk premium
        cost_of_debt = 0.05     # 5% cost of debt (could be estimated from credit ratings or interest coverage)
        
        # Enhanced factors
        size_premium = 0.0  # Could be based on market cap
        country_risk_premium = 0.0  # For international companies
        liquidity_premium = 0.0  # Could be based on trading volume
        
        return WACCInputs(
            risk_free_rate=risk_free_rate,
            market_premium=market_premium,
            beta=inputs.beta,
            tax_rate=inputs.tax_rate,
            debt_to_equity=inputs.debt_to_equity,
            cost_of_debt=cost_of_debt,
            size_premium=size_premium,
            country_risk_premium=country_risk_premium,
            liquidity_premium=liquidity_premium
        )

    def _get_valuation_weights(self, company_type: CompanyType) -> Dict[str, float]:
        """Get method weights based on company type"""
        weights = {
            CompanyType.MATURE: {'dcf': 0.5, 'pe': 0.2, 'ev_ebitda': 0.2, 'pb': 0.1},
            CompanyType.GROWTH: {'dcf': 0.6, 'pe': 0.2, 'ev_ebitda': 0.2, 'pb': 0.0},
            CompanyType.STARTUP: {'dcf': 0.4, 'pe': 0.3, 'ev_ebitda': 0.3, 'pb': 0.0},
            CompanyType.BANK: {'dcf': 0.0, 'pe': 0.4, 'ev_ebitda': 0.0, 'pb': 0.6},
            CompanyType.REIT: {'dcf': 0.2, 'pe': 0.2, 'ev_ebitda': 0.2, 'pb': 0.4},
            CompanyType.UTILITY: {'dcf': 0.4, 'pe': 0.2, 'ev_ebitda': 0.2, 'pb': 0.2},
            CompanyType.CYCLICAL: {'dcf': 0.3, 'pe': 0.3, 'ev_ebitda': 0.3, 'pb': 0.1},
        }
        return weights.get(company_type, weights[CompanyType.MATURE]) # Default to mature

    def _calculate_weighted_fair_value(self, method_values: Dict[str, float], weights: Dict[str, float]) -> float:
        """Calculate weighted average fair value"""
        total_weighted_value = 0
        total_weight = 0
        
        for method, value in method_values.items():
            weight = weights.get(method, 0)
            if value > 0: # Only include positive valuations
                total_weighted_value += value * weight
                total_weight += weight
                
        if total_weight > 0:
            return total_weighted_value / total_weight
        else:
            # Fallback if all methods failed
            valid_values = [v for v in method_values.values() if v > 0]
            return sum(valid_values) / len(valid_values) if valid_values else 0

    def perform_comprehensive_valuation(
        self, 
        ticker: str, 
        market_price: float = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Perform complete valuation analysis
        
        Args:
            ticker: Stock ticker symbol
            market_price: Current market price (optional, will be fetched if not provided)
            progress_callback: Optional callback function to report progress (e.g., for UI)
        """
        if progress_callback:
            progress_callback(f"Starting comprehensive valuation for {ticker}")
        else:
            # Fallback to Streamlit if no callback provided (but this is less ideal)
            st.info(f"🔍 Starting comprehensive valuation for {ticker}")
            
        try:
            # Get fundamental data
            if progress_callback: progress_callback("Fetching fundamental data...")
            fundamental_response = get_fundamental_data(ticker)
            if not fundamental_response.success or not fundamental_response.data:
                return {'error': f'No fundamental data available for {ticker}'}
            data = fundamental_response.data
            
            # Get current price if not provided
            if market_price is None:
                if progress_callback: progress_callback("Fetching live price...")
                price_response = get_live_price(ticker)
                market_price = price_response.data.get('price') if price_response.success else 50.0
            
            # Create company profile
            if progress_callback: progress_callback("Classifying company...")
            company_type, classification_confidence = IntelligentCompanyClassifier.classify_company(
                data, data.get('Sector', '')
            )
            profile = CompanyProfile(
                ticker=ticker,
                company_type=company_type,
                sector=data.get('Sector', 'Unknown'),
                industry=data.get('Industry', 'Unknown'),
                market_cap=safe_numeric(data.get('MarketCapitalization'), 1e9),
                revenue_growth_5y=safe_numeric(data.get('QuarterlyRevenueGrowthYOY'), 0.05),
                profit_margin=safe_numeric(data.get('ProfitMargin'), 0.05),
                debt_to_equity=safe_numeric(data.get('DebtToEquity'), 0.5),
                dividend_yield=safe_numeric(data.get('DividendYield'), 0.0),
                beta=safe_numeric(data.get('Beta'), 1.0)
            )
            
            # Create valuation inputs
            if progress_callback: progress_callback("Preparing valuation inputs...")
            inputs = self._create_valuation_inputs(data, profile)
            
            # Calculate WACC
            if progress_callback: progress_callback("Calculating WACC...")
            wacc_inputs = self._create_wacc_inputs(profile, inputs)
            wacc_result = self.wacc_calculator.calculate_comprehensive_wacc(wacc_inputs, profile)
            
            # Perform DCF valuation
            if progress_callback: progress_callback("Running DCF valuation...")
            dcf_result = self.dcf_calculator.calculate_comprehensive_dcf(inputs, wacc_result)
            
            # Comparable valuations
            if progress_callback: progress_callback("Running comparable valuations...")
            pe_valuation = self.comparable_calculator.calculate_pe_valuation(inputs)
            ev_ebitda_valuation = self.comparable_calculator.calculate_ev_ebitda_valuation(inputs)
            pb_valuation = self.comparable_calculator.calculate_price_to_book(inputs)
            
            # Risk assessment
            if progress_callback: progress_callback("Assessing risks...")
            risk_assessment = self.risk_assessor.assess_company_risk(inputs, profile)
            
            # Aggregate results with weighting based on company type
            valuation_weights = self._get_valuation_weights(company_type)
            weighted_fair_value = self._calculate_weighted_fair_value(
                {
                    'dcf': dcf_result['value_per_share'],
                    'pe': pe_valuation['fair_value'],
                    'ev_ebitda': ev_ebitda_valuation['fair_value'],
                    'pb': pb_valuation['fair_value']
                },
                valuation_weights
            )
            
            # Calculate upside/downside
            upside_potential = (weighted_fair_value - market_price) / market_price if market_price > 0 else 0
            
            if progress_callback: progress_callback("Valuation complete!")
            
            return {
                'ticker': ticker,
                'current_price': market_price,
                'fair_value_weighted': weighted_fair_value,
                'upside_potential': upside_potential,
                'company_profile': profile,
                'classification_confidence': classification_confidence,
                'valuation_methods': {
                    'dcf': dcf_result,
                    'pe_comparable': pe_valuation,
                    'ev_ebitda_comparable': ev_ebitda_valuation,
                    'price_to_book': pb_valuation
                },
                'method_weights': valuation_weights,
                'wacc_analysis': wacc_result,
                'risk_assessment': risk_assessment,
                'financial_inputs': inputs,
                'data_quality': {
                    'source': fundamental_response.source.value,
                    'confidence': fundamental_response.confidence.value,
                    'cache_hit': fundamental_response.cache_hit
                }
            }
        except Exception as e:
            logger.error(f"Comprehensive valuation failed for {ticker}: {e}")
            return {
                'error': f'Valuation failed: {str(e)}',
                'ticker': ticker,
                'current_price': market_price or 0
            }

# Global instance for easy access
valuation_engine = ComprehensiveValuationEngine()