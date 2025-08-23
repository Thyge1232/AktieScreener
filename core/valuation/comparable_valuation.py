# core/valuation/comparable_valuation.py
"""Modul til sammenligningsbaserede vÃ¦rdiansÃ¦ttelsesmetoder."""

import logging
from typing import Dict, Optional
from .dcf_engine import ValuationInputs # Bruges til input

logger = logging.getLogger(__name__)

class ComparableValuation:
    """Industry comparable valuation methods"""

    @staticmethod
    def calculate_pe_valuation(inputs: ValuationInputs, industry_pe: Optional[float] = None) -> Dict[str, float]:
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
    def calculate_ev_ebitda_valuation(inputs: ValuationInputs, industry_ev_ebitda: Optional[float] = None) -> Dict[str, float]:
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
