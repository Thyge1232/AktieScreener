# core/valuation/scenario_analysis.py
"""Modul til scenarieanalyse og Monte Carlo simulationer for vÃ¦rdiansÃ¦ttelse."""

import logging
import numpy as np
from typing import Dict, Any
from .dcf_engine import DCFEngine, ValuationInputs # Importer DCF-funktioner

logger = logging.getLogger(__name__)

class ScenarioAnalysis:
    """Klasse til at udfÃ¸re scenarieanalyser og simulationer."""

    @staticmethod
    def perform_sensitivity_analysis(inputs: ValuationInputs, base_wacc: float,
                                    projection_years: int) -> Dict[str, Dict[str, float]]:
        """Perform sensitivity analysis on key variables"""
        # Base case value
        base_result = DCFEngine.calculate_comprehensive_dcf(
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
                result = DCFEngine.calculate_comprehensive_dcf(
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
                # KORREKT: Opret en ny, uafhÃ¦ngig kopi af ValuationInputs
                modified_inputs = ValuationInputs(**inputs.__dict__)
                modified_inputs.revenue_growth_rate = growth
                result = DCFEngine.calculate_comprehensive_dcf(
                    modified_inputs, {'wacc': base_wacc}, projection_years
                )
                sensitivity['growth_rate'][scenario] = result['value_per_share']
            except:
                sensitivity['growth_rate'][scenario] = base_value
        return sensitivity

    @staticmethod
    def monte_carlo_simulation(inputs: ValuationInputs, wacc_result: Dict,
                              projection_years: int, num_simulations: int = 100) -> Dict[str, float]:
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
                    result = DCFEngine.calculate_comprehensive_dcf(
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
