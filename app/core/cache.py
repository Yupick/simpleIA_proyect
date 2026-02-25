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

    def get(self, prompt: str, *args, params: dict | None = None):
        """Get supports two call styles for backwards compatibility:
        - get(prompt, params_dict)
        - get(prompt, max_length, num_return_sequences, temperature)
        """
        # Legacy positional signature: prompt, max_length, num_return_sequences, temperature
        if args and not params:
            # If first arg is a dict, treat as params
            if isinstance(args[0], dict):
                params = args[0]
            elif len(args) >= 3:
                _, num_return_sequences, temperature = args[0], args[1], args[2]
                params = {
                    "max_length": args[0],
                    "num_return_sequences": num_return_sequences,
                    "temperature": temperature,
                }
            else:
                params = {}

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

    def set(self, prompt: str, *args, ttl: int | None = None, **kwargs):
        """Set supports backwards-compatible signatures:
        - set(prompt, params_dict, response, ttl=None)
        - legacy: set(prompt, response, max_length, num_return_sequences, temperature)
        """
        params = {}
        response = None

        # If called as set(prompt, params_dict, response)
        if args:
            if isinstance(args[0], dict):
                params = args[0]
                if len(args) > 1:
                    response = args[1]
            else:
                # legacy: set(prompt, response, max_length, num_return_sequences, temperature)
                response = args[0]
                if len(args) >= 4:
                    params = {
                        "max_length": args[1],
                        "num_return_sequences": args[2],
                        "temperature": args[3],
                    }

        # allow keyword usage: set(prompt, params=..., response=...)
        params = kwargs.get("params", params)
        if response is None:
            response = kwargs.get("response")

        ttl_use = ttl if ttl is not None else self.default_ttl
        key = self._make_key(prompt, params or {})
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

    # Backwards-compatible alias used across the codebase/tests
    def stats(self):
        return self.get_stats()


# Instancia global del cache
_llm_cache = LLMCache(max_size=100, default_ttl=3600)


def get_cache() -> LLMCache:
    """Retorna instancia global del cache."""
    return _llm_cache
