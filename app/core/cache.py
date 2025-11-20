"""
Cache LRU para respuestas de LLM.
Cachea por hash(prompt + parámetros) con TTL configurable.
"""

import hashlib
import time
from typing import Optional, Dict, Tuple
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class LLMCache:
    """Cache LRU simple con TTL para respuestas de modelos."""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        """
        Args:
            max_size: Número máximo de entradas en cache
            ttl_seconds: Tiempo de vida de cada entrada en segundos (default 1 hora)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[str, float]] = {}  # key -> (value, timestamp)
        self._access_order: list = []  # Para implementar LRU
        self._lock = Lock()
    
    def _make_key(self, prompt: str, max_length: int, num_return_sequences: int, temperature: float) -> str:
        """Genera una clave única basada en el prompt y parámetros."""
        data = f"{prompt}|{max_length}|{num_return_sequences}|{temperature}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def get(self, prompt: str, max_length: int = 50, num_return_sequences: int = 1, temperature: float = 0.7) -> Optional[str]:
        """
        Obtiene respuesta del cache si existe y no ha expirado.
        
        Returns:
            Respuesta cacheada o None si no existe o expiró
        """
        key = self._make_key(prompt, max_length, num_return_sequences, temperature)
        with self._lock:
            if key not in self._cache:
                logger.debug(f"[Cache] MISS: {key[:16]}...")
                return None
            
            value, timestamp = self._cache[key]
            # Verificar TTL
            if time.time() - timestamp > self.ttl_seconds:
                logger.debug(f"[Cache] EXPIRED: {key[:16]}...")
                del self._cache[key]
                self._access_order.remove(key)
                return None
            
            # Actualizar orden de acceso (LRU)
            self._access_order.remove(key)
            self._access_order.append(key)
            logger.debug(f"[Cache] HIT: {key[:16]}...")
            return value
    
    def set(self, prompt: str, response: str, max_length: int = 50, num_return_sequences: int = 1, temperature: float = 0.7):
        """
        Almacena respuesta en cache.
        Si se alcanza max_size, elimina el elemento menos recientemente usado.
        """
        key = self._make_key(prompt, max_length, num_return_sequences, temperature)
        with self._lock:
            # Si ya existe, actualizar timestamp
            if key in self._cache:
                self._access_order.remove(key)
            # Si cache lleno, eliminar LRU
            elif len(self._cache) >= self.max_size:
                lru_key = self._access_order.pop(0)
                del self._cache[lru_key]
                logger.debug(f"[Cache] EVICT LRU: {lru_key[:16]}...")
            
            self._cache[key] = (response, time.time())
            self._access_order.append(key)
            logger.debug(f"[Cache] SET: {key[:16]}... (total: {len(self._cache)})")
    
    def clear(self):
        """Limpia todo el cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            logger.info("[Cache] Cleared")
    
    def stats(self) -> Dict[str, int]:
        """Retorna estadísticas del cache."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds
            }

# Instancia global del cache
_llm_cache = LLMCache(max_size=100, ttl_seconds=3600)

def get_cache() -> LLMCache:
    """Retorna instancia global del cache."""
    return _llm_cache
