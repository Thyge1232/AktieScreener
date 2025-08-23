# core/data/rate_limiter.py
import time
import logging
import threading
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Union

logger = logging.getLogger(__name__)

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
            if self.backoff_until and now < self.backoff_until:
                remaining = (self.backoff_until - now).total_seconds()
                if remaining > 5:
                    st.warning(f"⏸️ Backing off for {remaining:.0f}s due to {self.source} failures")
                return False

            self.calls = [call_time for call_time in self.calls if now - call_time < timedelta(minutes=1)]

            if len(self.calls) >= self.calls_per_minute:
                sleep_time = 60 - (now - self.calls[0]).total_seconds() + 1
                if sleep_time > 0:
                    with st.spinner(f"⏱️ Rate limiting {self.source}: {sleep_time:.0f}s"):
                        time.sleep(sleep_time)
                    return self.wait_if_needed(operation_name)

            self.calls.append(now)
            self.total_calls += 1
            return True

    def register_failure(self, error_type: str = "unknown"):
        """Register API failure for intelligent backoff"""
        with self._lock:
            self.consecutive_failures += 1
            self.failed_calls += 1
            if "rate limit" in error_type.lower():
                backoff_seconds = 75
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