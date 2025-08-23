# core/valuation/valuation_inputs.py
"""Dataklasse til input for værdiansættelsesberegninger."""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class ValuationInputs:
    """Comprehensive valuation inputs with validation."""
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
