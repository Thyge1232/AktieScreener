# core/valuation/dcf_engine.py
"""Modul til Discounted Cash Flow (DCF) vÃ¦rdiansÃ¦ttelse."""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from .wacc_calculator import WACCInputs # Bruges ikke direkte her, men for konsistens
from ..data.api_client import safe_numeric # Antager denne funktion findes

logger = logging.getLogger(__name__)

# Antager ValuationInputs findes i en fÃ¦lles fil eller flyttes hertil
# from .valuation_inputs import ValuationInputs

@dataclass
class ValuationInputs:
    """Comprehensive valuation inputs with validation - Moved from valuation_engine.py"""
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

class DCFEngine:
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
        # Import her for at undgÃ¥ cirkulÃ¦re afhÃ¦ngigheder
        from .scenario_analysis import ScenarioAnalysis
        return ScenarioAnalysis.perform_sensitivity_analysis(inputs, base_wacc, projection_years)

    @staticmethod
    def _monte_carlo_simulation(inputs: ValuationInputs, wacc_result: Dict,
                              projection_years: int, num_simulations: int = 100) -> Dict[str, float]:
        """Monte Carlo simulation for confidence intervals"""
        # Import her for at undgÃ¥ cirkulÃ¦re afhÃ¦ngigheder
        from .scenario_analysis import ScenarioAnalysis
        return ScenarioAnalysis.monte_carlo_simulation(inputs, wacc_result, projection_years, num_simulations)

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
            validated_inputs = DCFEngine._validate_dcf_inputs(inputs)
            wacc = wacc_result['wacc']
            # Multi-stage growth model
            growth_stages = DCFEngine._create_growth_stages(validated_inputs, projection_years)
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
            sensitivity = DCFEngine._perform_sensitivity_analysis(
                validated_inputs, wacc, projection_years
            )
            # Monte Carlo simulation for confidence intervals
            confidence_intervals = DCFEngine._monte_carlo_simulation(
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
            return DCFEngine._fallback_dcf_result(inputs)
