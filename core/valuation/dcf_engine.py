# core/valuation/dcf_engine.py
import logging
import threading
from typing import Dict, List, Any

from .valuation_inputs import ValuationInputs
from .valuation_config import ValuationConfig

logger = logging.getLogger(__name__)

# Global, trådsikker rekursionsbeskyttelse
_dcf_recursion_guard = threading.local()

class DCFEngine:
    """Sophisticated DCF model with a clean separation between core calculation and advanced analysis."""

    @staticmethod
    def _validate_dcf_inputs(inputs: ValuationInputs) -> ValuationInputs:
        """Validate and enhance DCF inputs."""
        # Denne metode kan forblive den samme, da den forbereder input
        if inputs.free_cash_flow <= 0:
            if inputs.ebitda > 0:
                estimated_fcf = inputs.ebitda * (1 - inputs.tax_rate) - inputs.capex
                inputs.free_cash_flow = max(estimated_fcf, inputs.net_income * 0.6)
            elif inputs.net_income > 0:
                inputs.free_cash_flow = inputs.net_income * 0.7
            else:
                inputs.free_cash_flow = inputs.revenue * 0.03
        return inputs

    @staticmethod
    def _create_growth_stages(inputs: ValuationInputs, projection_years: int, config: ValuationConfig) -> List[Dict]:
        """Create multi-stage growth model based on configuration."""
        stages = []
        high_growth_years = min(config.dcf_high_growth_years_cap, projection_years)
        
        for year in range(high_growth_years):
            fade_factor = config.dcf_fade_factor ** year
            growth_rate = inputs.revenue_growth_rate * fade_factor
            stages.append({'growth_rate': growth_rate})
        
        remaining_years = projection_years - len(stages)
        for _ in range(remaining_years):
            stages.append({'growth_rate': inputs.terminal_growth_rate})
        return stages

    @staticmethod
    def calculate_core_dcf(inputs: ValuationInputs, wacc: float, projection_years: int, config: ValuationConfig) -> Dict[str, Any]:
        """
        Core DCF calculation without advanced analysis. Safe for use in other modules.
        """
        if getattr(_dcf_recursion_guard, 'is_running', False):
            raise RecursionError("Circular call detected in DCF core calculation.")
        
        _dcf_recursion_guard.is_running = True
        try:
            if not (0.02 <= wacc <= 0.30):
                wacc = 0.10

            growth_stages = DCFEngine._create_growth_stages(inputs, projection_years, config)
            
            projected_fcf, cumulative_pv = [], 0
            current_fcf = inputs.free_cash_flow
            
            for year, stage_info in enumerate(growth_stages, 1):
                current_fcf *= (1 + stage_info['growth_rate'])
                pv_fcf = current_fcf / ((1 + wacc) ** year)
                projected_fcf.append({'year': year, 'fcf': current_fcf, 'pv_fcf': pv_fcf})
                cumulative_pv += pv_fcf

            terminal_fcf = current_fcf * (1 + inputs.terminal_growth_rate)
            if wacc <= inputs.terminal_growth_rate:
                raise ValueError("WACC must be greater than terminal growth rate.")
                
            terminal_value = terminal_fcf / (wacc - inputs.terminal_growth_rate)
            pv_terminal = terminal_value / ((1 + wacc) ** projection_years)

            enterprise_value = cumulative_pv + pv_terminal
            net_debt = max(0, inputs.total_debt - inputs.cash_and_equivalents)
            equity_value = max(0, enterprise_value - net_debt)
            
            if inputs.shares_outstanding <= 0:
                raise ValueError("Shares outstanding must be positive.")
            value_per_share = equity_value / inputs.shares_outstanding

            return {
                'enterprise_value': enterprise_value, 'equity_value': equity_value,
                'value_per_share': value_per_share, 'terminal_value': terminal_value,
                'pv_terminal': pv_terminal, 'pv_explicit_period': cumulative_pv,
                'terminal_value_percentage': pv_terminal / enterprise_value if enterprise_value > 0 else 0,
                'projected_fcf': projected_fcf,
                'assumptions': {'wacc': wacc, 'terminal_growth': inputs.terminal_growth_rate}
            }
        except Exception as e:
            logger.error(f"Core DCF calculation failed: {e}")
            raise
        finally:
            _dcf_recursion_guard.is_running = False

    @staticmethod
    def calculate_comprehensive_dcf(
        inputs: ValuationInputs, 
        wacc_result: Dict,
        projection_years: int,
        config: ValuationConfig
    ) -> Dict[str, Any]:
        """
        Full DCF orchestrator that performs base calculation and adds advanced analysis.
        """
        from .scenario_analysis import ScenarioAnalysis

        try:
            validated_inputs = DCFEngine._validate_dcf_inputs(inputs)
            base_wacc = wacc_result.get('wacc', 0.10)

            base_result = DCFEngine.calculate_core_dcf(
                validated_inputs, base_wacc, projection_years, config
            )

            sensitivity = ScenarioAnalysis.perform_sensitivity_analysis(
                inputs=validated_inputs, base_wacc=base_wacc,
                projection_years=projection_years, 
                base_value_per_share=base_result['value_per_share'],
                config=config
            )

            confidence_intervals = ScenarioAnalysis.monte_carlo_simulation(
                validated_inputs, wacc_result, projection_years, config
            )

            final_result = base_result.copy()
            final_result.update({
                'sensitivity_analysis': sensitivity,
                'confidence_intervals': confidence_intervals
            })
            
            return final_result
        except Exception as e:
            logger.error(f"Comprehensive DCF calculation failed: {e}", exc_info=True)
            return DCFEngine._fallback_dcf_result(inputs)

    @staticmethod
    def _fallback_dcf_result(inputs: ValuationInputs) -> Dict[str, Any]:
        """Fallback DCF result when a calculation fails."""
        value = 0
        if inputs.shares_outstanding > 0:
            value = (inputs.free_cash_flow * 15) / inputs.shares_outstanding
        
        return {
            'value_per_share': value,
            'error': 'Calculation failed, showing fallback result.',
            'assumptions': {'note': 'Fallback calculation used.'}
        }