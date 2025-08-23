# core/data/config.py

from dataclasses import dataclass, field
from typing import Dict, Tuple

@dataclass
class AppConfig:
    """Centralized configuration management for the data layer."""
    api_config: Dict[str, Dict] = field(default_factory=lambda: {
        'alpha_vantage': {'calls_per_minute': 5, 'timeout': 15, 'retry_attempts': 3, 'backoff_factor': 2.0},
        'yfinance': {'timeout': 10, 'retry_attempts': 2, 'backoff_factor': 1.5}
    })
    cache_config: Dict[str, int] = field(default_factory=lambda: {
        'live_price': 300, 'fundamental': 3600, 'historical_daily': 86400,
        'historical_weekly': 604800, 'company_profile': 604800
    })
    validation_ranges: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        'PERatio': (0, 500), 'MarketCapitalization': (1e6, 1e15), 'DividendYield': (0, 0.50),
        'Beta': (-5, 5), 'DebtToEquity': (0, 50), 'RevenueTTM': (1e3, 1e15),
        'NetIncomeTTM': (-1e14, 1e15), 'EPS': (-1000, 1000)
    })

# Global configuration instance that other modules will import
config = AppConfig()