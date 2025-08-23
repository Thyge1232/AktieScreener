# core/data/caching.py
import os
import sqlite3
import hashlib
import json
import time
import logging
import threading
from datetime import datetime
from typing import Optional, Any, Dict

# RETTELSE: Kun denne ene import af 'config' skal være her.
from .config import config

logger = logging.getLogger(__name__)

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
                    key TEXT PRIMARY KEY, data TEXT NOT NULL, timestamp REAL NOT NULL,
                    ttl INTEGER NOT NULL, data_type TEXT NOT NULL,
                    access_count INTEGER DEFAULT 1, size_bytes INTEGER DEFAULT 0
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON cache(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_data_type ON cache(data_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_expiry ON cache(timestamp + ttl)')

    def get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """Generate unique cache key with better collision resistance"""
        sorted_kwargs = sorted(kwargs.items())
        key_data = f"{func_name}:{str(args)}:{str(sorted_kwargs)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get_cached_result(self, func_name: str, data_type: str, *args, **kwargs) -> Optional[Any]:
        """Get cached result with automatic cleanup"""
        cache_key = self.get_cache_key(func_name, *args, **kwargs)
        ttl = config.cache_config.get(data_type, 1800)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT data, timestamp FROM cache WHERE key = ? AND ? - timestamp < ttl', (cache_key, time.time()))
            row = cursor.fetchone()
            if row:
                try:
                    conn.execute('UPDATE cache SET access_count = access_count + 1 WHERE key = ?', (cache_key,))
                    result = json.loads(row[0])
                    logger.debug(f"Cache hit for {func_name}")
                    return result
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Cache corruption for {cache_key}: {e}")
                    conn.execute("DELETE FROM cache WHERE key = ?", (cache_key,))
        self._maybe_cleanup()
        return None

    def save_to_cache(self, result: Any, func_name: str, data_type: str, *args, **kwargs):
        """Save result to cache with metadata"""
        if result is None: return
        cache_key = self.get_cache_key(func_name, *args, **kwargs)
        ttl = config.cache_config.get(data_type, 1800)
        try:
            data_json = json.dumps(result, default=str)
            data_size = len(data_json.encode())
            if data_size > 1024 * 1024:
                logger.warning(f"Skipping cache for {func_name}: data too large ({data_size} bytes)")
                return
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('INSERT OR REPLACE INTO cache (key, data, timestamp, ttl, data_type, access_count, size_bytes) VALUES (?, ?, ?, ?, ?, 1, ?)', (cache_key, data_json, time.time(), ttl, data_type, data_size))
            logger.debug(f"Cached {func_name} ({data_size} bytes)")
        except Exception as e:
            logger.error(f"Cache save error for {func_name}: {e}")

    def _maybe_cleanup(self):
        """Periodic cleanup of expired entries"""
        with self._cleanup_lock:
            now = datetime.now()
            if (now - self._last_cleanup).total_seconds() < 3600: return
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute('DELETE FROM cache WHERE ? - timestamp >= ttl', (time.time(),))
                    deleted = cursor.rowcount
                    cursor = conn.execute('SELECT COUNT(*), SUM(size_bytes) FROM cache')
                    count, total_size = cursor.fetchone()
                    if total_size and total_size > 50 * 1024 * 1024:
                        conn.execute('DELETE FROM cache WHERE key NOT IN (SELECT key FROM cache ORDER BY access_count DESC LIMIT ?)', (count // 2,))
                self._last_cleanup = now
                if deleted > 0:
                    logger.info(f"Cache cleanup: removed {deleted} expired entries")
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT data_type, COUNT(*) FROM cache WHERE ? - timestamp < ttl GROUP BY data_type', (time.time(),))
                stats_by_type = {row[0]: row[1] for row in cursor.fetchall()}
                cursor = conn.execute('SELECT COUNT(*), SUM(size_bytes), AVG(access_count) FROM cache WHERE ? - timestamp < ttl', (time.time(),))
                total, size, avg_access = cursor.fetchone()
                return {
                    'total_entries': total or 0, 'total_size_mb': (size or 0) / 1024 / 1024,
                    'avg_access_count': avg_access or 0, 'entries_by_type': stats_by_type
                }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}