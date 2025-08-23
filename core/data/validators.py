# core/data/validators.py
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

# RETTELSE: Kun denne ene import af 'config' skal være her.
from .config import config


class AdvancedDataValidator:
    """Enhanced data validation with ML-style outlier detection"""

    @classmethod
    def validate_financial_data(cls, data: Dict[str, Any], ticker: str) -> Tuple[Dict[str, Any], List[str]]:
        """Comprehensive data validation with warnings"""
        if not data:
            return {}, ["No data provided"]

        cleaned = {}
        warnings = []

        for key, value in data.items():
            if key in config.validation_ranges:
                min_val, max_val = config.validation_ranges[key]
                numeric_val = cls.safe_numeric(value)

                if numeric_val is not None:
                    if min_val <= numeric_val <= max_val:
                        cleaned[key] = numeric_val
                    else:
                        warnings.append(f"{key}: {numeric_val} outside range [{min_val}, {max_val}]")
                        # Use median of range as fallback for extreme outliers
                        if key == 'PERatio' and numeric_val > max_val:
                            cleaned[key] = 25.0  # Reasonable PE fallback
                        elif key == 'Beta' and abs(numeric_val) > max_val:
                            cleaned[key] = 1.0  # Market beta
                        else:
                            cleaned[key] = None
                else:
                    cleaned[key] = None
                    if value not in [None, '', 'None', 'N/A']:
                        warnings.append(f"{key}: Cannot convert '{value}' to numeric")
            else:
                cleaned[key] = value

        # Cross-validation checks
        cls._cross_validate_metrics(cleaned, warnings, ticker)

        return cleaned, warnings

    @classmethod
    def _cross_validate_metrics(cls, data: Dict[str, Any], warnings: List[str], ticker: str):
        """Cross-validate related financial metrics"""
        pe = data.get('PERatio')
        eps = data.get('EPS')
        market_cap = data.get('MarketCapitalization')
        revenue = data.get('RevenueTTM')

        if pe and eps and pe > 0 and eps > 0:
            implied_price = pe * eps
            if market_cap and market_cap > 0:
                shares_est = market_cap / implied_price
                if shares_est < 1000:
                    warnings.append(f"Potential data inconsistency: P/E ({pe}) × EPS ({eps}) vs Market Cap")

        if revenue and market_cap and revenue > 0 and market_cap > 0:
            price_to_sales = market_cap / revenue
            if price_to_sales > 50:
                warnings.append(f"High P/S ratio ({price_to_sales:.1f}) - verify {ticker} data")

    @staticmethod
    def safe_numeric(value, default=None) -> Optional[float]:
        """Enhanced numeric conversion with better parsing"""
        if pd.isna(value) or value is None or value == '':
            return default

        if isinstance(value, (int, float)):
            if np.isnan(value) or np.isinf(value):
                return default
            return float(value)

        if isinstance(value, str):
            cleaned = value.strip().upper()
            if cleaned in ['N/A', 'NONE', '-', '--', 'NULL']:
                return default
            cleaned = cleaned.replace(',', '').replace('$', '').replace('%', '')
            multiplier = 1
            if cleaned.endswith(('K', 'M', 'B', 'T')):
                suffix = cleaned[-1]
                cleaned = cleaned[:-1]
                multiplier = {'K': 1e3, 'M': 1e6, 'B': 1e9, 'T': 1e12}[suffix]
            try:
                return float(cleaned) * multiplier
            except ValueError:
                return default
        return default

# Gør funktionen let tilgængelig for import
safe_numeric = AdvancedDataValidator.safe_numeric