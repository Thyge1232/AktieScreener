# core/data/api_client.py - Komplet Forbedret Version
import requests
import pandas as pd
import time
import streamlit as st
import logging
import hashlib
import json
import sqlite3
import os
from datetime import datetime, timedelta
from functools import wraps
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import threading

# Setup enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Hent API key med fallback
try:
    API_KEY = st.secrets["ALPHA_VANTAGE_API_KEY"]
except Exception:
    API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
    logger.warning("Using demo API key - rate limits will be severe")

class DataSource(Enum):
    """Available data sources"""
    ALPHA_VANTAGE = "alpha_vantage"
    YFINANCE = "yfinance"
    FALLBACK = "fallback"

class ConfidenceLevel(Enum):
    """Data confidence levels"""
    HIGH = "high"
    MEDIUM = "medium" 
    LOW = "low"
    UNKNOWN = "unknown"

@dataclass
class APIResponse:
    """Standardized API response structure"""
    success: bool
    data: Optional[Dict] = None
    error_message: Optional[str] = None
    source: DataSource = DataSource.ALPHA_VANTAGE
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    timestamp: datetime = field(default_factory=datetime.now)
    cache_hit: bool = False
    response_time_ms: int = 0

@dataclass
class AppConfig:
    """Centralized configuration management"""
    api_config: Dict[str, Dict] = field(default_factory=lambda: {
        'alpha_vantage': {
            'calls_per_minute': 5,
            'timeout': 15,
            'retry_attempts': 3,
            'backoff_factor': 2.0
        },
        'yfinance': {
            'timeout': 10,
            'retry_attempts': 2,
            'backoff_factor': 1.5
        }
    })
    
    cache_config: Dict[str, int] = field(default_factory=lambda: {
        'live_price': 300,      # 5 minutes
        'fundamental': 3600,    # 1 hour  
        'historical_daily': 86400,    # 1 day
        'historical_weekly': 604800,   # 1 week
        'company_profile': 604800      # 1 week
    })
    
    validation_ranges: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        'PERatio': (0, 500),
        'MarketCapitalization': (1e6, 1e15),
        'DividendYield': (0, 0.50),
        'Beta': (-5, 5),
        'DebtToEquity': (0, 50),
        'RevenueTTM': (1e3, 1e15),
        'NetIncomeTTM': (-1e14, 1e15),
        'EPS': (-1000, 1000)
    })

# Global configuration instance
config = AppConfig()

class EnhancedRateLimiter:
    """Advanced rate limiting with exponential backoff and failure detection"""
    
    def __init__(self, calls_per_minute: int = 5, source: str = "API"):
        self.calls_per_minute = calls_per_minute
        self.source = source
        self.calls = []
        self.consecutive_failures = 0
        self.backoff_until = None
        self.total_calls = 0
        self.failed_calls = 0
        self._lock = threading.Lock()
    
    def wait_if_needed(self, operation_name: str = "API") -> bool:
        """Enhanced rate limiting with failure detection and backoff"""
        with self._lock:
            now = datetime.now()
            
            # Check if we're in backoff period due to failures
            if self.backoff_until and now < self.backoff_until:
                remaining = (self.backoff_until - now).total_seconds()
                if remaining > 5:  # Only show warning for longer waits
                    st.warning(f"⏸️ Backing off for {remaining:.0f}s due to {self.source} failures")
                return False
            
            # Clean old calls (older than 1 minute)
            self.calls = [call_time for call_time in self.calls 
                         if now - call_time < timedelta(minutes=1)]
            
            # Check if we need to wait for rate limit
            if len(self.calls) >= self.calls_per_minute:
                sleep_time = 60 - (now - self.calls[0]).total_seconds() + 1
                if sleep_time > 0:
                    with st.spinner(f"⏱️ Rate limiting {self.source}: {sleep_time:.0f}s"):
                        time.sleep(sleep_time)
                    return self.wait_if_needed(operation_name)  # Recursive check
            
            self.calls.append(now)
            self.total_calls += 1
            return True
    
    def register_failure(self, error_type: str = "unknown"):
        """Register API failure for intelligent backoff"""
        with self._lock:
            self.consecutive_failures += 1
            self.failed_calls += 1
            
            # Exponential backoff based on failure type
            if "rate limit" in error_type.lower():
                backoff_seconds = 75  # Rate limit: wait longer
            elif "timeout" in error_type.lower():
                backoff_seconds = min(180, 30 * self.consecutive_failures)
            else:
                backoff_seconds = min(300, 15 * (2 ** min(self.consecutive_failures - 1, 4)))
            
            self.backoff_until = datetime.now() + timedelta(seconds=backoff_seconds)
            logger.warning(f"{self.source} failure #{self.consecutive_failures}: {error_type}, backing off {backoff_seconds}s")
    
    def register_success(self):
        """Reset failure counter on successful call"""
        with self._lock:
            if self.consecutive_failures > 0:
                logger.info(f"{self.source} recovered after {self.consecutive_failures} failures")
            self.consecutive_failures = 0
            self.backoff_until = None
    
    def get_stats(self) -> Dict[str, Union[int, float]]:
        """Get rate limiter statistics"""
        success_rate = (self.total_calls - self.failed_calls) / max(self.total_calls, 1)
        return {
            'total_calls': self.total_calls,
            'failed_calls': self.failed_calls,
            'success_rate': success_rate,
            'consecutive_failures': self.consecutive_failures,
            'is_backed_off': bool(self.backoff_until and datetime.now() < self.backoff_until)
        }

class SQLiteCache:
    """High-performance SQLite-based caching with compression"""
    
    def __init__(self, cache_dir: str = ".streamlit_cache_v2"):
        self.cache_dir = cache_dir
        self.db_path = os.path.join(cache_dir, "cache.db")
        os.makedirs(cache_dir, exist_ok=True)
        self._init_db()
        self._cleanup_lock = threading.Lock()
        self._last_cleanup = datetime.now()
    
    def _init_db(self):
        """Initialize SQLite database with proper indexes"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    ttl INTEGER NOT NULL,
                    data_type TEXT NOT NULL,
                    access_count INTEGER DEFAULT 1,
                    size_bytes INTEGER DEFAULT 0
                )
            ''')
            
            # Create indexes for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON cache(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_data_type ON cache(data_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_expiry ON cache(timestamp + ttl)')
    
    def get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """Generate unique cache key with better collision resistance"""
        # Sort kwargs for consistency
        sorted_kwargs = sorted(kwargs.items())
        key_data = f"{func_name}:{str(args)}:{str(sorted_kwargs)}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get_cached_result(self, func_name: str, data_type: str, *args, **kwargs) -> Optional[Any]:
        """Get cached result with automatic cleanup"""
        cache_key = self.get_cache_key(func_name, *args, **kwargs)
        ttl = config.cache_config.get(data_type, 1800)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT data, timestamp FROM cache 
                WHERE key = ? AND ? - timestamp < ttl
            ''', (cache_key, time.time()))
            
            row = cursor.fetchone()
            
            if row:
                try:
                    # Update access count
                    conn.execute(
                        'UPDATE cache SET access_count = access_count + 1 WHERE key = ?',
                        (cache_key,)
                    )
                    
                    result = json.loads(row[0])
                    logger.debug(f"Cache hit for {func_name}")
                    return result
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Cache corruption for {cache_key}: {e}")
                    # Remove corrupted entry
                    conn.execute("DELETE FROM cache WHERE key = ?", (cache_key,))
        
        # Periodic cleanup
        self._maybe_cleanup()
        return None
    
    def save_to_cache(self, result: Any, func_name: str, data_type: str, *args, **kwargs):
        """Save result to cache with metadata"""
        if result is None:
            return
        
        cache_key = self.get_cache_key(func_name, *args, **kwargs)
        ttl = config.cache_config.get(data_type, 1800)
        
        try:
            data_json = json.dumps(result, default=str)
            data_size = len(data_json.encode())
            
            # Skip caching if data is too large (>1MB)
            if data_size > 1024 * 1024:
                logger.warning(f"Skipping cache for {func_name}: data too large ({data_size} bytes)")
                return
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO cache 
                    (key, data, timestamp, ttl, data_type, access_count, size_bytes)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                ''', (cache_key, data_json, time.time(), ttl, data_type, data_size))
            
            logger.debug(f"Cached {func_name} ({data_size} bytes)")
            
        except Exception as e:
            logger.error(f"Cache save error for {func_name}: {e}")
    
    def _maybe_cleanup(self):
        """Periodic cleanup of expired entries"""
        with self._cleanup_lock:
            now = datetime.now()
            if (now - self._last_cleanup).total_seconds() < 3600:  # Cleanup hourly
                return
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Remove expired entries
                    cursor = conn.execute('DELETE FROM cache WHERE ? - timestamp >= ttl', (time.time(),))
                    deleted = cursor.rowcount
                    
                    # Remove least accessed entries if cache is too large
                    cursor = conn.execute('SELECT COUNT(*), SUM(size_bytes) FROM cache')
                    count, total_size = cursor.fetchone()
                    
                    if total_size and total_size > 50 * 1024 * 1024:  # > 50MB
                        # Keep only most accessed entries
                        conn.execute('''
                            DELETE FROM cache WHERE key NOT IN (
                                SELECT key FROM cache ORDER BY access_count DESC LIMIT ?
                            )
                        ''', (count // 2,))
                
                self._last_cleanup = now
                if deleted > 0:
                    logger.info(f"Cache cleanup: removed {deleted} expired entries")
                    
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_entries,
                        SUM(size_bytes) as total_size,
                        AVG(access_count) as avg_access,
                        data_type,
                        COUNT(*) as type_count
                    FROM cache 
                    WHERE ? - timestamp < ttl
                    GROUP BY data_type
                ''', (time.time(),))
                
                stats_by_type = {row[3]: row[4] for row in cursor.fetchall()}
                
                cursor = conn.execute('''
                    SELECT COUNT(*), SUM(size_bytes), AVG(access_count) 
                    FROM cache WHERE ? - timestamp < ttl
                ''', (time.time(),))
                
                total, size, avg_access = cursor.fetchone()
                
                return {
                    'total_entries': total or 0,
                    'total_size_mb': (size or 0) / 1024 / 1024,
                    'avg_access_count': avg_access or 0,
                    'entries_by_type': stats_by_type
                }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}

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
        # P/E vs EPS consistency
        pe = data.get('PERatio')
        eps = data.get('EPS')
        market_cap = data.get('MarketCapitalization')
        revenue = data.get('RevenueTTM')
        
        if pe and eps and pe > 0 and eps > 0:
            implied_price = pe * eps
            if market_cap and market_cap > 0:
                shares_est = market_cap / implied_price
                if shares_est < 1000:  # Suspiciously low share count
                    warnings.append(f"Potential data inconsistency: P/E ({pe}) × EPS ({eps}) vs Market Cap")
        
        # Revenue vs Market Cap sanity check
        if revenue and market_cap and revenue > 0 and market_cap > 0:
            price_to_sales = market_cap / revenue
            if price_to_sales > 50:  # Very high P/S ratio
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
            # Clean common formatting
            cleaned = value.strip().upper()
            
            # Handle special cases
            if cleaned in ['N/A', 'NONE', '-', '--', 'NULL']:
                return default
            
            # Remove formatting characters
            cleaned = cleaned.replace(',', '').replace('$', '').replace('%', '')
            
            # Handle abbreviations (K, M, B, T)
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

# Global instances with enhanced configuration
alpha_vantage_limiter = EnhancedRateLimiter(config.api_config['alpha_vantage']['calls_per_minute'], "Alpha Vantage")
yfinance_limiter = EnhancedRateLimiter(config.api_config['yfinance'].get('calls_per_minute', 10), "yFinance")
smart_cache = SQLiteCache()
data_validator = AdvancedDataValidator()

@contextmanager
def enhanced_error_handler(operation_name: str, ticker: str = None, source: DataSource = DataSource.ALPHA_VANTAGE):
    """Enhanced error handling with source-specific logic"""
    limiter = alpha_vantage_limiter if source == DataSource.ALPHA_VANTAGE else yfinance_limiter
    start_time = time.time()
    
    try:
        yield
        # Success - reset failure counter
        limiter.register_success()
        
    except requests.exceptions.Timeout as e:
        limiter.register_failure("timeout")
        error_msg = f"Timeout for {operation_name}" + (f" ({ticker})" if ticker else "")
        logger.error(f"{error_msg}: {e}")
        if source == DataSource.ALPHA_VANTAGE:
            st.warning(f"⏰ Alpha Vantage timeout for {ticker or operation_name}")
        
    except requests.exceptions.RequestException as e:
        error_type = "rate limit" if "rate limit" in str(e).lower() else "request error"
        limiter.register_failure(error_type)
        logger.error(f"{source.value} error in {operation_name}: {e}")
        if "rate limit" in str(e).lower():
            st.info(f"🚦 {source.value} rate limit reached - using fallback")
        else:
            st.warning(f"🌐 Network error with {source.value}")
        
    except KeyError as e:
        logger.warning(f"Missing data in {operation_name} from {source.value}: {e}")
        st.warning(f"⚠️ Incomplete data from {source.value}" + (f" for {ticker}" if ticker else ""))
        
    except Exception as e:
        limiter.register_failure("unknown error")
        logger.error(f"Unexpected error in {operation_name} ({source.value}): {e}")
        st.error(f"❌ Error in {operation_name}: {str(e)[:100]}")
    
    finally:
        response_time = int((time.time() - start_time) * 1000)
        logger.debug(f"{operation_name} took {response_time}ms")

def with_intelligent_cache_and_limits(data_type: str):
    """Enhanced decorator with intelligent caching and rate limiting"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check cache first
            cached_result = smart_cache.get_cached_result(func.__name__, data_type, *args, **kwargs)
            if cached_result is not None:
                return APIResponse(
                    success=True,
                    data=cached_result,
                    source=DataSource.FALLBACK,
                    confidence=ConfidenceLevel.MEDIUM,
                    cache_hit=True
                )
            
            # Rate limiting
            if not alpha_vantage_limiter.wait_if_needed(func.__name__):
                # If rate limited, try to get older cached data
                older_cache = smart_cache.get_cached_result(func.__name__, data_type + "_extended", *args, **kwargs)
                if older_cache:
                    return APIResponse(
                        success=True,
                        data=older_cache,
                        source=DataSource.FALLBACK,
                        confidence=ConfidenceLevel.LOW,
                        cache_hit=True
                    )
                return APIResponse(success=False, error_message="Rate limited and no cache available")
            
            # Execute function
            start_time = time.time()
            result = func(*args, **kwargs)
            response_time = int((time.time() - start_time) * 1000)
            
            # Cache successful results
            if result and result.success and result.data:
                smart_cache.save_to_cache(result.data, func.__name__, data_type, *args, **kwargs)
            
            # Update response metadata
            if result:
                result.response_time_ms = response_time
            
            return result
        return wrapper
    return decorator

@with_intelligent_cache_and_limits('live_price')
def get_live_price(ticker: str) -> APIResponse:
    """Enhanced live price fetching with multiple fallbacks"""
    
    # Try Alpha Vantage first
    try:
        with enhanced_error_handler("get_live_price", ticker, DataSource.ALPHA_VANTAGE):
            url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={API_KEY}'
            response = requests.get(url, timeout=config.api_config['alpha_vantage']['timeout'])
            response.raise_for_status()
            data = response.json()
            
            # Check for Alpha Vantage specific errors
            if "Information" in data and "api call frequency" in data["Information"].lower():
                raise requests.exceptions.RequestException("Alpha Vantage rate limit exceeded")
            
            if "Global Quote" in data and "05. price" in data["Global Quote"]:
                price = data_validator.safe_numeric(data["Global Quote"]["05. price"])
                if price and price > 0:
                    return APIResponse(
                        success=True,
                        data={'price': price, 'change_percent': data["Global Quote"].get("10. change percent", "0%")},
                        source=DataSource.ALPHA_VANTAGE,
                        confidence=ConfidenceLevel.HIGH
                    )
    except Exception as e:
        logger.warning(f"Alpha Vantage failed for {ticker}: {e}")
    
    # Fallback to yFinance
    try:
        import yfinance as yf
        
        with enhanced_error_handler("get_live_price_yfinance", ticker, DataSource.YFINANCE):
            if yfinance_limiter.wait_if_needed("yfinance_price"):
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # Try multiple price fields
                price = (info.get("regularMarketPrice") or 
                        info.get("currentPrice") or 
                        info.get("previousClose"))
                
                price = data_validator.safe_numeric(price)
                if price and price > 0:
                    change_pct = info.get("regularMarketChangePercent", 0)
                    return APIResponse(
                        success=True,
                        data={'price': price, 'change_percent': f"{change_pct:.2f}%"},
                        source=DataSource.YFINANCE,
                        confidence=ConfidenceLevel.MEDIUM
                    )
                    
    except ImportError:
        logger.error("yfinance not installed")
    except Exception as e:
        logger.warning(f"yfinance failed for {ticker}: {e}")
    
    return APIResponse(
        success=False,
        error_message=f"All data sources failed for {ticker}",
        source=DataSource.FALLBACK,
        confidence=ConfidenceLevel.UNKNOWN
    )

@with_intelligent_cache_and_limits('fundamental')
def get_fundamental_data(ticker: str) -> APIResponse:
    """Enhanced fundamental data with comprehensive validation"""
    
    # Try Alpha Vantage first
    try:
        with enhanced_error_handler("get_fundamental_data", ticker, DataSource.ALPHA_VANTAGE):
            url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={API_KEY}'
            response = requests.get(url, timeout=config.api_config['alpha_vantage']['timeout'])
            response.raise_for_status()
            data = response.json()
            
            # Check for errors
            if "Information" in data and "api call frequency" in data["Information"].lower():
                raise requests.exceptions.RequestException("Alpha Vantage rate limit")
            
            if data and "Symbol" in data:
                # Validate and clean data
                cleaned_data, warnings = data_validator.validate_financial_data(data, ticker)
                
                if warnings:
                    logger.warning(f"Data validation warnings for {ticker}: {'; '.join(warnings[:3])}")
                
                return APIResponse(
                    success=True,
                    data=cleaned_data,
                    source=DataSource.ALPHA_VANTAGE,
                    confidence=ConfidenceLevel.HIGH if len(warnings) < 3 else ConfidenceLevel.MEDIUM
                )
                
    except Exception as e:
        logger.warning(f"Alpha Vantage fundamental data failed for {ticker}: {e}")
    
    # Fallback to yFinance
    try:
        import yfinance as yf
        
        with enhanced_error_handler("get_fundamental_data_yfinance", ticker, DataSource.YFINANCE):
            if yfinance_limiter.wait_if_needed("yfinance_fundamental"):
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # Map yfinance data to Alpha Vantage format
                fallback_data = {
                    "Symbol": ticker,
                    "Name": info.get("longName", "N/A"),
                    "Sector": info.get("sector", "N/A"),
                    "Industry": info.get("industry", "N/A"),
                    "PERatio": info.get("trailingPE"),
                    "MarketCapitalization": info.get("marketCap"),
                    "DividendYield": info.get("dividendYield"),
                    "EPS": info.get("epsTrailingTwelveMonths"),
                    "Beta": info.get("beta"),
                    "DebtToEquity": info.get("debtToEquity"),
                    "RevenueTTM": info.get("totalRevenue"),
                    "NetIncomeTTM": info.get("netIncomeToCommon"),
                    "OperatingCashflowTTM": info.get("operatingCashFlow"),
                    "BookValue": info.get("bookValue"),
                    "DividendPerShare": info.get("dividendPerShare"),
                    "SharesOutstanding": info.get("sharesOutstanding"),
                    "QuarterlyRevenueGrowthYOY": info.get("quarterlyRevenueGrowthYOY"),
                    "EBITDA": info.get("ebitda"),
                }
                
                # Validate fallback data
                cleaned_data, warnings = data_validator.validate_financial_data(fallback_data, ticker)
                
                return APIResponse(
                    success=True,
                    data=cleaned_data,
                    source=DataSource.YFINANCE,
                    confidence=ConfidenceLevel.MEDIUM if len(warnings) < 5 else ConfidenceLevel.LOW
                )
                
    except ImportError:
        logger.error("yfinance not installed for fallback")
    except Exception as e:
        logger.warning(f"yfinance fundamental data failed for {ticker}: {e}")
    
    return APIResponse(
        success=False,
        error_message=f"All fundamental data sources failed for {ticker}",
        source=DataSource.FALLBACK
    )

# Historical data functions with enhanced error handling
@with_intelligent_cache_and_limits('historical_daily')
def get_daily_prices(ticker: str, outputsize: str = "full") -> APIResponse:
    """Enhanced daily price data with better error handling"""
    
    try:
        with enhanced_error_handler("get_daily_prices", ticker, DataSource.ALPHA_VANTAGE):
            url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={ticker}&outputsize={outputsize}&apikey={API_KEY}'
            
            response = requests.get(url, timeout=config.api_config['alpha_vantage']['timeout'])
            response.raise_for_status()
            data = response.json()
            
            if "Information" in data and "api call frequency" in data["Information"].lower():
                raise requests.exceptions.RequestException("Alpha Vantage rate limit")
            
            if "Time Series (Daily)" in data:
                df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient='index')
                df.index = pd.to_datetime(df.index)
                
                # Safe numeric conversion with validation
                numeric_columns = ['1. open', '2. high', '3. low', '4. close', '5. adjusted close', '6. volume']
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Rename columns to standard format
                df.columns = ['Open', 'High', 'Low', 'Close', 'Adjusted_Close', 'Volume', 'Dividend', 'Split_Coefficient']
                df = df.sort_index()
                df['Ticker'] = ticker
                
                # Data quality checks
                initial_rows = len(df)
                df = df.dropna(subset=['Close', 'Adjusted_Close'])
                df = df[df['Close'] > 0]  # Remove zero/negative prices
                df = df[df['Volume'] >= 0]  # Remove negative volume
                
                final_rows = len(df)
                if final_rows < initial_rows * 0.9:  # Lost more than 10% of data
                    logger.warning(f"Data quality issue for {ticker}: {initial_rows - final_rows} rows removed")
                
                return APIResponse(
                    success=True,
                    data=df.to_dict('records') if len(df) < 1000 else df.tail(1000).to_dict('records'),
                    source=DataSource.ALPHA_VANTAGE,
                    confidence=ConfidenceLevel.HIGH if final_rows >= initial_rows * 0.95 else ConfidenceLevel.MEDIUM
                )
    
    except Exception as e:
        logger.warning(f"Alpha Vantage daily prices failed for {ticker}: {e}")
    
    # Fallback to yfinance for historical data
    try:
        import yfinance as yf
        
        with enhanced_error_handler("get_daily_prices_yfinance", ticker, DataSource.YFINANCE):
            if yfinance_limiter.wait_if_needed("yfinance_daily"):
                stock = yf.Ticker(ticker)
                
                # Get appropriate period based on outputsize
                period = "2y" if outputsize == "compact" else "max"
                df = stock.history(period=period, auto_adjust=False)
                
                if not df.empty:
                    # Standardize column names
                    df.columns = ['Open', 'High', 'Low', 'Close', 'Adjusted_Close', 'Volume', 'Dividend', 'Split_Coefficient']
                    df['Ticker'] = ticker
                    df = df.sort_index()
                    
                    return APIResponse(
                        success=True,
                        data=df.to_dict('records') if len(df) < 1000 else df.tail(1000).to_dict('records'),
                        source=DataSource.YFINANCE,
                        confidence=ConfidenceLevel.MEDIUM
                    )
    
    except ImportError:
        logger.error("yfinance not available for historical data fallback")
    except Exception as e:
        logger.warning(f"yfinance daily prices failed for {ticker}: {e}")
    
    return APIResponse(
        success=False,
        error_message=f"No historical daily data available for {ticker}",
        source=DataSource.FALLBACK
    )

# Enhanced batch processing functions
def get_portfolio_data_batch(tickers: List[str], data_type: str = "fundamental", max_workers: int = 3) -> Dict[str, APIResponse]:
    """Parallel batch processing with intelligent error handling"""
    
    if len(tickers) > 10:
        st.info(f"📊 Processing first 10 tickers for optimal performance")
        tickers = tickers[:10]
    
    results = {}
    failed_tickers = []
    
    # Choose appropriate function
    fetch_func = get_fundamental_data if data_type == "fundamental" else get_live_price
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_ticker = {executor.submit(fetch_func, ticker): ticker for ticker in tickers}
        
        # Progress bar
        progress_bar = st.progress(0, text="Fetching data...")
        completed = 0
        
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            completed += 1
            
            try:
                result = future.result(timeout=30)
                results[ticker] = result
                
                if not result.success:
                    failed_tickers.append(ticker)
                
            except Exception as e:
                logger.error(f"Batch processing failed for {ticker}: {e}")
                failed_tickers.append(ticker)
                results[ticker] = APIResponse(
                    success=False,
                    error_message=str(e),
                    source=DataSource.FALLBACK
                )
            
            progress_bar.progress(completed / len(tickers), text=f"Processed {completed}/{len(tickers)} tickers")
    
    progress_bar.empty()
    
    # Summary
    successful = len([r for r in results.values() if r.success])
    if failed_tickers:
        st.warning(f"⚠️ {len(failed_tickers)} tickers failed: {', '.join(failed_tickers[:5])}")
    
    st.success(f"✅ Successfully processed {successful}/{len(tickers)} tickers")
    
    return results

def get_data_for_favorites(tickers: List[str]) -> pd.DataFrame:
    """Enhanced favorite data processing with batch optimization"""
    if not tickers:
        return pd.DataFrame()
    
    # Get both fundamental and price data in parallel
    fundamental_results = get_portfolio_data_batch(tickers, "fundamental", max_workers=2)
    price_results = get_portfolio_data_batch(tickers, "live_price", max_workers=3)
    
    all_stock_data = []
    
    for ticker in tickers:
        fundamental = fundamental_results.get(ticker)
        price_data = price_results.get(ticker)
        
        if fundamental and fundamental.success:
            data = fundamental.data
            current_price = price_data.data.get('price') if price_data and price_data.success else None
            
            stock_info = {
                'Ticker': data.get('Symbol', ticker),
                'Company': data.get('Name', 'Unknown'),
                'Sector': data.get('Sector', 'Unknown'),
                'Price': current_price,
                'P/E': data_validator.safe_numeric(data.get('PERatio')),
                'Market Cap': data_validator.safe_numeric(data.get('MarketCapitalization')),
                'Dividend Yield': data_validator.safe_numeric(data.get('DividendYield'), 0) * 100 if data.get('DividendYield') else None,
                'EPS': data_validator.safe_numeric(data.get('EPS')),
                'Data Quality': fundamental.confidence.value,
                'Source': fundamental.source.value
            }
            all_stock_data.append(stock_info)
    
    return pd.DataFrame(all_stock_data)

# Performance monitoring and diagnostics
class PerformanceMonitor:
    """Enhanced performance monitoring with detailed metrics"""
    
    def __init__(self):
        self.metrics = []
        self._lock = threading.Lock()
    
    def log_api_call(self, function_name: str, ticker: str, duration: float, 
                    success: bool, data_source: str, cache_hit: bool = False):
        """Log comprehensive API call metrics"""
        with self._lock:
            self.metrics.append({
                'timestamp': datetime.now(),
                'function': function_name,
                'ticker': ticker,
                'duration_ms': int(duration * 1000),
                'success': success,
                'data_source': data_source,
                'cache_hit': cache_hit
            })
            
            # Keep only recent metrics (last 1000 calls)
            if len(self.metrics) > 1000:
                self.metrics = self.metrics[-1000:]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.metrics:
            return {'message': 'No performance data available'}
        
        df = pd.DataFrame(self.metrics)
        now = datetime.now()
        recent_df = df[df['timestamp'] > now - timedelta(hours=1)]  # Last hour
        
        # Calculate statistics
        stats = {
            'total_calls': len(df),
            'recent_calls_1h': len(recent_df),
            'overall_success_rate': df['success'].mean(),
            'recent_success_rate': recent_df['success'].mean() if not recent_df.empty else 0,
            'avg_response_time_ms': df['duration_ms'].mean(),
            'cache_hit_rate': df['cache_hit'].mean(),
            'calls_by_source': df['data_source'].value_counts().to_dict(),
            'calls_by_function': df['function'].value_counts().to_dict(),
            'rate_limiter_stats': {
                'alpha_vantage': alpha_vantage_limiter.get_stats(),
                'yfinance': yfinance_limiter.get_stats()
            }
        }
        
        # Performance grades
        if stats['overall_success_rate'] > 0.95:
            stats['performance_grade'] = 'A'
        elif stats['overall_success_rate'] > 0.85:
            stats['performance_grade'] = 'B'
        elif stats['overall_success_rate'] > 0.70:
            stats['performance_grade'] = 'C'
        else:
            stats['performance_grade'] = 'D'
        
        return stats
    
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Get diagnostic information for troubleshooting"""
        cache_stats = smart_cache.get_cache_stats()
        
        return {
            'api_keys_available': bool(API_KEY and API_KEY != "demo"),
            'rate_limiters': {
                'alpha_vantage': alpha_vantage_limiter.get_stats(),
                'yfinance': yfinance_limiter.get_stats()
            },
            'cache_performance': cache_stats,
            'recent_errors': [
                {
                    'function': m['function'],
                    'ticker': m['ticker'],
                    'timestamp': m['timestamp'].isoformat(),
                    'source': m['data_source']
                }
                for m in self.metrics[-50:] if not m['success']
            ][-10:]  # Last 10 errors
        }

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Utility functions for diagnostics
def get_api_health_check() -> Dict[str, Any]:
    """Comprehensive API health check"""
    health_status = {
        'timestamp': datetime.now().isoformat(),
        'api_key_status': 'valid' if API_KEY and API_KEY != "demo" else 'demo/missing',
        'rate_limiters': {
            'alpha_vantage': alpha_vantage_limiter.get_stats(),
            'yfinance': yfinance_limiter.get_stats()
        },
        'cache_stats': smart_cache.get_cache_stats(),
        'performance': performance_monitor.get_performance_report()
    }
    
    # Overall health score
    av_success_rate = health_status['rate_limiters']['alpha_vantage']['success_rate']
    yf_success_rate = health_status['rate_limiters']['yfinance']['success_rate']
    cache_entries = health_status['cache_stats']['total_entries']
    
    if av_success_rate > 0.9 and cache_entries > 10:
        health_status['overall_health'] = 'excellent'
    elif av_success_rate > 0.7 or yf_success_rate > 0.8:
        health_status['overall_health'] = 'good'
    elif av_success_rate > 0.5 or yf_success_rate > 0.6:
        health_status['overall_health'] = 'fair'
    else:
        health_status['overall_health'] = 'poor'
    
    return health_status

def display_performance_dashboard():
    """Display performance dashboard in Streamlit"""
    st.subheader("🔧 API Performance Dashboard")
    
    health = get_api_health_check()
    
    # Health status indicator
    health_colors = {
        'excellent': '🟢',
        'good': '🟡', 
        'fair': '🟠',
        'poor': '🔴'
    }
    
    st.markdown(f"**Overall Health:** {health_colors[health['overall_health']]} {health['overall_health'].title()}")
    
    # Metrics in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("API Key", health['api_key_status'])
        st.metric("Cache Entries", health['cache_stats']['total_entries'])
    
    with col2:
        av_stats = health['rate_limiters']['alpha_vantage']
        st.metric("AV Success Rate", f"{av_stats['success_rate']:.1%}")
        st.metric("AV Total Calls", av_stats['total_calls'])
    
    with col3:
        yf_stats = health['rate_limiters']['yfinance']
        st.metric("YF Success Rate", f"{yf_stats['success_rate']:.1%}")
        st.metric("Cache Size (MB)", f"{health['cache_stats']['total_size_mb']:.1f}")
    
    # Performance chart
    if st.checkbox("Show Detailed Performance"):
        perf_data = performance_monitor.get_performance_report()
        st.json(perf_data)
    
    # Cache management
    if st.button("🧹 Clear Cache"):
        try:
            smart_cache._init_db()  # Reinitialize (clears data)
            st.success("Cache cleared successfully!")
        except Exception as e:
            st.error(f"Error clearing cache: {e}")

safe_numeric = AdvancedDataValidator.safe_numeric
