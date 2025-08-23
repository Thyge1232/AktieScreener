# core/data/client.py
import requests
import pandas as pd
import time
import streamlit as st
import logging
import os
from datetime import datetime, timedelta
from functools import wraps
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# --- Nye, lokale imports fra de opdelte filer ---
from .caching import SQLiteCache
from .rate_limiter import EnhancedRateLimiter
from .validators import AdvancedDataValidator, safe_numeric
# NYT: Importer den centrale konfiguration
from .config import config, AppConfig

# Setup enhanced logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Hent API key med fallback
try:
    API_KEY = st.secrets["ALPHA_VANTAGE_API_KEY"]
except Exception:
    API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
    logger.warning("Using demo API key - rate limits will be severe")

# --- Datastrukturer og Konfiguration (centralt placeret her) ---
class DataSource(Enum):
    ALPHA_VANTAGE = "alpha_vantage"
    YFINANCE = "yfinance"
    FALLBACK = "fallback"

class ConfidenceLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"

@dataclass
class APIResponse:
    success: bool
    data: Optional[Dict] = None
    error_message: Optional[str] = None
    source: DataSource = DataSource.ALPHA_VANTAGE
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    timestamp: datetime = field(default_factory=datetime.now)
    cache_hit: bool = False
    response_time_ms: int = 0


# --- Globale Instanser (bruger de importerede klasser) ---
alpha_vantage_limiter = EnhancedRateLimiter(config.api_config['alpha_vantage']['calls_per_minute'], "Alpha Vantage")
yfinance_limiter = EnhancedRateLimiter(config.api_config['yfinance'].get('calls_per_minute', 10), "yFinance")
smart_cache = SQLiteCache()
data_validator = AdvancedDataValidator()

# --- Decorator og Fejlhåndtering ---
@contextmanager
def enhanced_error_handler(operation_name: str, ticker: str = None, source: DataSource = DataSource.ALPHA_VANTAGE):
    limiter = alpha_vantage_limiter if source == DataSource.ALPHA_VANTAGE else yfinance_limiter
    start_time = time.time()
    try:
        yield
        limiter.register_success()
    except requests.exceptions.Timeout as e:
        limiter.register_failure("timeout")
        logger.error(f"Timeout for {operation_name} ({ticker}): {e}")
    except requests.exceptions.RequestException as e:
        error_type = "rate limit" if "rate limit" in str(e).lower() else "request error"
        limiter.register_failure(error_type)
        logger.error(f"{source.value} error in {operation_name}: {e}")
    except Exception as e:
        limiter.register_failure("unknown error")
        logger.error(f"Unexpected error in {operation_name} ({source.value}): {e}")

def with_intelligent_cache_and_limits(data_type: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cached_result = smart_cache.get_cached_result(func.__name__, data_type, *args, **kwargs)
            if cached_result is not None:
                return APIResponse(success=True, data=cached_result, source=DataSource.FALLBACK, confidence=ConfidenceLevel.MEDIUM, cache_hit=True)
            
            if not alpha_vantage_limiter.wait_if_needed(func.__name__):
                return APIResponse(success=False, error_message="Rate limited and no cache available")
            
            start_time = time.time()
            result = func(*args, **kwargs)
            response_time = int((time.time() - start_time) * 1000)
            
            if result and result.success and result.data:
                smart_cache.save_to_cache(result.data, func.__name__, data_type, *args, **kwargs)
            
            if result: result.response_time_ms = response_time
            return result
        return wrapper
    return decorator

# --- API Kald Funktioner ---
@with_intelligent_cache_and_limits('live_price')
def get_live_price(ticker: str) -> APIResponse:
    """Enhanced live price fetching with multiple fallbacks"""
    try:
        with enhanced_error_handler("get_live_price", ticker, DataSource.ALPHA_VANTAGE):
            url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={API_KEY}'
            response = requests.get(url, timeout=config.api_config['alpha_vantage']['timeout'])
            response.raise_for_status()
            data = response.json()
            if "Information" in data and "api call frequency" in data["Information"].lower():
                raise requests.exceptions.RequestException("Alpha Vantage rate limit exceeded")
            if "Global Quote" in data and "05. price" in data["Global Quote"]:
                price = data_validator.safe_numeric(data["Global Quote"]["05. price"])
                if price and price > 0:
                    return APIResponse(success=True, data={'price': price, 'change_percent': data["Global Quote"].get("10. change percent", "0%")}, source=DataSource.ALPHA_VANTAGE, confidence=ConfidenceLevel.HIGH)
    except Exception as e:
        logger.warning(f"Alpha Vantage failed for {ticker}: {e}")
    
    try:
        import yfinance as yf
        with enhanced_error_handler("get_live_price_yfinance", ticker, DataSource.YFINANCE):
            if yfinance_limiter.wait_if_needed("yfinance_price"):
                stock = yf.Ticker(ticker)
                info = stock.info
                price = (info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose"))
                price = data_validator.safe_numeric(price)
                if price and price > 0:
                    change_pct = info.get("regularMarketChangePercent", 0)
                    return APIResponse(success=True, data={'price': price, 'change_percent': f"{change_pct:.2f}%"}, source=DataSource.YFINANCE, confidence=ConfidenceLevel.MEDIUM)
    except ImportError:
        logger.error("yfinance not installed")
    except Exception as e:
        logger.warning(f"yfinance failed for {ticker}: {e}")
    
    return APIResponse(success=False, error_message=f"All data sources failed for {ticker}", source=DataSource.FALLBACK, confidence=ConfidenceLevel.UNKNOWN)

@with_intelligent_cache_and_limits('fundamental')
def get_fundamental_data(ticker: str) -> APIResponse:
    """Enhanced fundamental data with comprehensive validation"""
    try:
        with enhanced_error_handler("get_fundamental_data", ticker, DataSource.ALPHA_VANTAGE):
            url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={API_KEY}'
            response = requests.get(url, timeout=config.api_config['alpha_vantage']['timeout'])
            response.raise_for_status()
            data = response.json()
            if "Information" in data and "api call frequency" in data["Information"].lower():
                raise requests.exceptions.RequestException("Alpha Vantage rate limit")
            if data and "Symbol" in data:
                cleaned_data, warnings = data_validator.validate_financial_data(data, ticker)
                if warnings:
                    logger.warning(f"Data validation warnings for {ticker}: {'; '.join(warnings[:3])}")
                return APIResponse(success=True, data=cleaned_data, source=DataSource.ALPHA_VANTAGE, confidence=ConfidenceLevel.HIGH if len(warnings) < 3 else ConfidenceLevel.MEDIUM)
    except Exception as e:
        logger.warning(f"Alpha Vantage fundamental data failed for {ticker}: {e}")

    try:
        import yfinance as yf
        with enhanced_error_handler("get_fundamental_data_yfinance", ticker, DataSource.YFINANCE):
            if yfinance_limiter.wait_if_needed("yfinance_fundamental"):
                stock = yf.Ticker(ticker)
                info = stock.info
                fallback_data = {
                    "Symbol": ticker, "Name": info.get("longName", "N/A"), "Sector": info.get("sector", "N/A"),
                    "Industry": info.get("industry", "N/A"), "PERatio": info.get("trailingPE"),
                    "MarketCapitalization": info.get("marketCap"), "DividendYield": info.get("dividendYield"),
                    "EPS": info.get("epsTrailingTwelveMonths"), "Beta": info.get("beta"),
                    "DebtToEquity": info.get("debtToEquity"), "RevenueTTM": info.get("totalRevenue"),
                    "NetIncomeTTM": info.get("netIncomeToCommon"), "OperatingCashflowTTM": info.get("operatingCashFlow"),
                    "BookValue": info.get("bookValue"), "DividendPerShare": info.get("dividendPerShare"),
                    "SharesOutstanding": info.get("sharesOutstanding"), "QuarterlyRevenueGrowthYOY": info.get("quarterlyRevenueGrowthYOY"),
                    "EBITDA": info.get("ebitda"),
                }
                cleaned_data, warnings = data_validator.validate_financial_data(fallback_data, ticker)
                return APIResponse(success=True, data=cleaned_data, source=DataSource.YFINANCE, confidence=ConfidenceLevel.MEDIUM if len(warnings) < 5 else ConfidenceLevel.LOW)
    except ImportError:
        logger.error("yfinance not installed for fallback")
    except Exception as e:
        logger.warning(f"yfinance fundamental data failed for {ticker}: {e}")
    
    return APIResponse(success=False, error_message=f"All fundamental data sources failed for {ticker}", source=DataSource.FALLBACK)

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
                numeric_columns = ['1. open', '2. high', '3. low', '4. close', '5. adjusted close', '6. volume']
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                df.columns = ['Open', 'High', 'Low', 'Close', 'Adjusted_Close', 'Volume', 'Dividend', 'Split_Coefficient']
                df = df.sort_index(); df['Ticker'] = ticker
                initial_rows = len(df)
                df = df.dropna(subset=['Close', 'Adjusted_Close']); df = df[df['Close'] > 0]; df = df[df['Volume'] >= 0]
                final_rows = len(df)
                if final_rows < initial_rows * 0.9:
                    logger.warning(f"Data quality issue for {ticker}: {initial_rows - final_rows} rows removed")
                return APIResponse(success=True, data=df.to_dict('records'), source=DataSource.ALPHA_VANTAGE, confidence=ConfidenceLevel.HIGH if final_rows >= initial_rows * 0.95 else ConfidenceLevel.MEDIUM)
    except Exception as e:
        logger.warning(f"Alpha Vantage daily prices failed for {ticker}: {e}")

    try:
        import yfinance as yf
        with enhanced_error_handler("get_daily_prices_yfinance", ticker, DataSource.YFINANCE):
            if yfinance_limiter.wait_if_needed("yfinance_daily"):
                stock = yf.Ticker(ticker)
                period = "2y" if outputsize == "compact" else "max"
                df = stock.history(period=period, auto_adjust=False)
                if not df.empty:
                    df.columns = ['Open', 'High', 'Low', 'Close', 'Adjusted_Close', 'Volume', 'Dividend', 'Split_Coefficient']
                    df['Ticker'] = ticker; df = df.sort_index()
                    return APIResponse(success=True, data=df.to_dict('records'), source=DataSource.YFINANCE, confidence=ConfidenceLevel.MEDIUM)
    except ImportError:
        logger.error("yfinance not available for historical data fallback")
    except Exception as e:
        logger.warning(f"yfinance daily prices failed for {ticker}: {e}")
    
    return APIResponse(success=False, error_message=f"No historical daily data available for {ticker}", source=DataSource.FALLBACK)

# --- Batch Processing og Hjælpefunktioner ---
def get_portfolio_data_batch(tickers: List[str], data_type: str = "fundamental", max_workers: int = 3) -> Dict[str, APIResponse]:
    """Parallel batch processing with intelligent error handling"""
    results = {}
    failed_tickers = []
    fetch_func = get_fundamental_data if data_type == "fundamental" else get_live_price
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {executor.submit(fetch_func, ticker): ticker for ticker in tickers}
        progress_bar = st.progress(0, text="Fetching data...")
        completed = 0
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            completed += 1
            try:
                result = future.result(timeout=30)
                results[ticker] = result
                if not result.success: failed_tickers.append(ticker)
            except Exception as e:
                logger.error(f"Batch processing failed for {ticker}: {e}")
                failed_tickers.append(ticker)
                results[ticker] = APIResponse(success=False, error_message=str(e), source=DataSource.FALLBACK)
            progress_bar.progress(completed / len(tickers), text=f"Processed {completed}/{len(tickers)} tickers")
    progress_bar.empty()
    return results

def get_data_for_favorites(tickers: List[str]) -> pd.DataFrame:
    """Enhanced favorite data processing with batch optimization"""
    if not tickers: return pd.DataFrame()
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
                'Ticker': data.get('Symbol', ticker), 'Company': data.get('Name', 'Unknown'),
                'Sector': data.get('Sector', 'Unknown'), 'Price': current_price,
                'P/E': safe_numeric(data.get('PERatio')), 'Market Cap': safe_numeric(data.get('MarketCapitalization')),
                'Dividend Yield': safe_numeric(data.get('DividendYield'), 0) * 100 if data.get('DividendYield') else None,
                'EPS': safe_numeric(data.get('EPS')), 'Data Quality': fundamental.confidence.value,
                'Source': fundamental.source.value
            }
            all_stock_data.append(stock_info)
    return pd.DataFrame(all_stock_data)

# --- Performance Monitorering ---
class PerformanceMonitor:
    """Enhanced performance monitoring with detailed metrics"""
    def __init__(self):
        self.metrics = []
        self._lock = threading.Lock()
    
    def log_api_call(self, function_name: str, ticker: str, duration: float, success: bool, data_source: str, cache_hit: bool = False):
        with self._lock:
            self.metrics.append({'timestamp': datetime.now(), 'function': function_name, 'ticker': ticker, 'duration_ms': int(duration * 1000), 'success': success, 'data_source': data_source, 'cache_hit': cache_hit})
            if len(self.metrics) > 1000: self.metrics = self.metrics[-1000:]
    
    def get_performance_report(self) -> Dict[str, Any]:
        if not self.metrics: return {'message': 'No performance data available'}
        df = pd.DataFrame(self.metrics)
        recent_df = df[df['timestamp'] > datetime.now() - timedelta(hours=1)]
        stats = {
            'total_calls': len(df), 'recent_calls_1h': len(recent_df),
            'overall_success_rate': df['success'].mean(),
            'recent_success_rate': recent_df['success'].mean() if not recent_df.empty else 0,
            'avg_response_time_ms': df['duration_ms'].mean(), 'cache_hit_rate': df['cache_hit'].mean(),
            'calls_by_source': df['data_source'].value_counts().to_dict(),
            'calls_by_function': df['function'].value_counts().to_dict(),
            'rate_limiter_stats': {'alpha_vantage': alpha_vantage_limiter.get_stats(), 'yfinance': yfinance_limiter.get_stats()}
        }
        if stats['overall_success_rate'] > 0.95: stats['performance_grade'] = 'A'
        elif stats['overall_success_rate'] > 0.85: stats['performance_grade'] = 'B'
        else: stats['performance_grade'] = 'C'
        return stats

performance_monitor = PerformanceMonitor()

def get_api_health_check() -> Dict[str, Any]:
    """Comprehensive API health check"""
    health_status = {
        'timestamp': datetime.now().isoformat(),
        'api_key_status': 'valid' if API_KEY and API_KEY != "demo" else 'demo/missing',
        'rate_limiters': {'alpha_vantage': alpha_vantage_limiter.get_stats(), 'yfinance': yfinance_limiter.get_stats()},
        'cache_stats': smart_cache.get_cache_stats(),
        'performance': performance_monitor.get_performance_report()
    }
    av_success_rate = health_status['rate_limiters']['alpha_vantage']['success_rate']
    cache_entries = health_status['cache_stats'].get('total_entries', 0)
    if av_success_rate > 0.9 and cache_entries > 10: health_status['overall_health'] = 'excellent'
    elif av_success_rate > 0.7: health_status['overall_health'] = 'good'
    else: health_status['overall_health'] = 'poor'
    return health_status

def display_performance_dashboard():
    """Display performance dashboard in Streamlit"""
    st.subheader("🔧 API Performance Dashboard")
    health = get_api_health_check()
    health_colors = {'excellent': '🟢', 'good': '🟡', 'fair': '🟠', 'poor': '🔴'}
    st.markdown(f"**Overall Health:** {health_colors.get(health['overall_health'], '❓')} {health['overall_health'].title()}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("API Key", health['api_key_status'])
        st.metric("Cache Entries", health['cache_stats'].get('total_entries', 'N/A'))
    with col2:
        av_stats = health['rate_limiters']['alpha_vantage']
        st.metric("AV Success Rate", f"{av_stats['success_rate']:.1%}")
    with col3:
        st.metric("Cache Size (MB)", f"{health['cache_stats'].get('total_size_mb', 0):.1f}")
    if st.button("🧹 Clear Cache"):
        try:
            smart_cache._init_db()
            st.success("Cache cleared successfully!")
        except Exception as e:
            st.error(f"Error clearing cache: {e}")