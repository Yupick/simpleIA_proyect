"""
Cache LRU para respuestas de LLM.
Cachea por hash(prompt + parámetros) con TTL configurable.
"""

import hashlib
import time
from typing import Dict, Tuple
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class LLMCache:
    """Cache LRU para respuestas de modelos, compatible con tests.

    API expected by tests:
      - __init__(max_size, default_ttl)
      - set(prompt, params: dict, response, ttl=None)
      - get(prompt, params: dict)
      - clear(), get_stats()
    """

    def __init__(self, max_size: int = 100, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Tuple[object, float, int]] = {}
        # key -> (value, timestamp, ttl)
        self._access_order: list = []
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, prompt: str, params: dict) -> str:
        # Normalize params by sorting items to keep key consistent
        items = tuple(sorted(params.items())) if isinstance(params, dict) else tuple()
        data = f"{prompt}|{items}"
        return hashlib.sha256(str(data).encode()).hexdigest()

    def get(self, prompt: str, params: dict = None):
        params = params or {}
        key = self._make_key(prompt, params)
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            value, ts, ttl = self._cache[key]
            if time.time() - ts > ttl:
                # expired
                del self._cache[key]
                try:
                    self._access_order.remove(key)
                except ValueError:
                    pass
                self._misses += 1
                return None

            # update LRU order
            try:
                self._access_order.remove(key)
            except ValueError:
                pass
            self._access_order.append(key)
            self._hits += 1
            return value

    def set(self, prompt: str, params: dict, response, ttl: int = None):
        params = params or {}
        key = self._make_key(prompt, params)
        ttl_use = ttl if ttl is not None else self.default_ttl
        with self._lock:
            if key in self._cache:
                try:
                    self._access_order.remove(key)
                except ValueError:
                    pass
            elif len(self._cache) >= self.max_size:
                # evict LRU
                lru = self._access_order.pop(0)
                if lru in self._cache:
                    del self._cache[lru]

            self._cache[key] = (response, time.time(), ttl_use)
            self._access_order.append(key)

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self):
        with self._lock:
            size = len(self._cache)
            hit_rate = (
                self._hits / (self._hits + self._misses)
                if (self._hits + self._misses) > 0
                else 0.0
            )
            return {
                "size": size,
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
            }


# Instancia global del cache
_llm_cache = LLMCache(max_size=100, default_ttl=3600)


def get_cache() -> LLMCache:
    """Retorna instancia global del cache."""
    return _llm_cache
