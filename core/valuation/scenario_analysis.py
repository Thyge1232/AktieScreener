# core/valuation/scenario_analysis.py
"""Modul til scenarieanalyse og Monte Carlo simulationer for værdiansættelse."""

import logging
import numpy as np
from typing import Dict, Any

from .valuation_inputs import ValuationInputs
from .valuation_config import ValuationConfig

logger = logging.getLogger(__name__)

class ScenarioAnalysis:
    """Klasse til at udføre scenarieanalyser og simulationer."""

    @staticmethod
    def perform_sensitivity_analysis(
        inputs: ValuationInputs, 
        base_wacc: float,
        projection_years: int,
        base_value_per_share: float,
        config: ValuationConfig
    ) -> Dict[str, Dict[str, float]]:
        """Perform sensitivity analysis using configurable variations and the core DCF calculation."""
        # Lokal import for at undgå cirkulære afhængigheder på modulniveau
        from .dcf_engine import DCFEngine

        sensitivity = {}
        
        # Hent variationsparametre fra den centrale konfiguration
        wacc_var = config.sensitivity_wacc_variation
        growth_var = config.sensitivity_growth_variation

        # WACC sensitivity
        wacc_scenarios = {
            'low_wacc': base_wacc * (1 - wacc_var), 
            'high_wacc': base_wacc * (1 + wacc_var)
        }
        sensitivity['wacc'] = {}
        for scenario, wacc in wacc_scenarios.items():
            try:
                # Kald den lette, sikre kerneberegning
                result = DCFEngine.calculate_core_dcf(inputs, wacc, projection_years, config)
                sensitivity['wacc'][scenario] = result['value_per_share']
            except Exception as e:
                logger.warning(f"Sensitivity scenario '{scenario}' failed: {e}")
                sensitivity['wacc'][scenario] = base_value_per_share
        
        # Growth rate sensitivity
        growth_scenarios = {
            'low_growth': inputs.revenue_growth_rate * (1 - growth_var), 
            'high_growth': inputs.revenue_growth_rate * (1 + growth_var)
        }
        sensitivity['growth_rate'] = {}
        for scenario, growth in growth_scenarios.items():
            try:
                modified_inputs = inputs.__class__(**inputs.__dict__)
                modified_inputs.revenue_growth_rate = growth
                # Kald den lette, sikre kerneberegning igen
                result = DCFEngine.calculate_core_dcf(modified_inputs, base_wacc, projection_years, config)
                sensitivity['growth_rate'][scenario] = result['value_per_share']
            except Exception as e:
                logger.warning(f"Sensitivity scenario '{scenario}' failed: {e}")
                sensitivity['growth_rate'][scenario] = base_value_per_share
        
        return sensitivity

    @staticmethod
    def monte_carlo_simulation(
        inputs: ValuationInputs, 
        wacc_result: Dict,
        projection_years: int, 
        config: ValuationConfig
    ) -> Dict[str, float]:
        """Monte Carlo simulation for confidence intervals."""
        # Lokal import for at undgå cirkulære afhængigheder på modulniveau
        from .dcf_engine import DCFEngine

        values = []
        base_wacc = wacc_result.get('wacc', 0.10)
        num_simulations = min(config.monte_carlo_simulations_default, config.monte_carlo_performance_limit)
        
        for _ in range(num_simulations):
            try:
                wacc_variation = np.random.normal(0, 0.015)
                growth_variation = np.random.normal(0, 0.02)
                
                scenario_inputs = inputs.__class__(**inputs.__dict__)
                scenario_inputs.revenue_growth_rate += growth_variation
                scenario_wacc = base_wacc + wacc_variation
                
                # Kald den lette, sikre kerneberegning i simulationen
                result = DCFEngine.calculate_core_dcf(scenario_inputs, scenario_wacc, projection_years, config)
                values.append(result['value_per_share'])
            except Exception:
                continue

        if len(values) > 10:
            values = np.array(values)
            return {
                'p10': float(np.percentile(values, 10)), 'p25': float(np.percentile(values, 25)),
                'p50': float(np.percentile(values, 50)), 'p75': float(np.percentile(values, 75)),
                'p90': float(np.percentile(values, 90)), 'mean': float(np.mean(values)),
                'std': float(np.std(values))
            }
        
        # Fallback hvis simulationen giver for få resultater
        base_value = 0
        if inputs.shares_outstanding > 0:
            base_value = (inputs.free_cash_flow / inputs.shares_outstanding) * 15
        
        return {
            'p50': base_value, 'mean': base_value, 'std': base_value * 0.2,
            'p10': base_value * 0.7, 'p90': base_value * 1.3
        }