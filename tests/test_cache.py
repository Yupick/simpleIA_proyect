"""Tests para cache LRU de respuestas LLM"""
import pytest
import time
from app.core.cache import LLMCache


class TestLLMCache:
    """Tests para funcionalidad cache LRU"""
    
    def test_cache_basic_set_get(self):
        """Validar set y get básico"""
        cache = LLMCache(max_size=3, default_ttl=60)
        
        cache.set("prompt1", {"param": "value"}, "response1")
        result = cache.get("prompt1", {"param": "value"})
        
        assert result == "response1"
    
    def test_cache_miss(self):
        """Validar cache miss retorna None"""
        cache = LLMCache(max_size=3, default_ttl=60)
        
        result = cache.get("nonexistent", {})
        
        assert result is None
    
    def test_cache_key_consistency(self):
        """Validar mismo prompt+params genera mismo key"""
        cache = LLMCache(max_size=3, default_ttl=60)
        
        cache.set("prompt", {"temp": 0.7, "max": 50}, "response1")
        # Orden diferente de params
        result = cache.get("prompt", {"max": 50, "temp": 0.7})
        
        assert result == "response1"
    
    def test_cache_different_params(self):
        """Validar diferentes params generan diferentes keys"""
        cache = LLMCache(max_size=3, default_ttl=60)
        
        cache.set("prompt", {"temp": 0.7}, "response1")
        cache.set("prompt", {"temp": 0.9}, "response2")
        
        result1 = cache.get("prompt", {"temp": 0.7})
        result2 = cache.get("prompt", {"temp": 0.9})
        
        assert result1 == "response1"
        assert result2 == "response2"
    
    def test_cache_lru_eviction(self):
        """Validar eviction LRU cuando max_size alcanzado"""
        cache = LLMCache(max_size=3, default_ttl=60)
        
        # Llenar cache
        cache.set("prompt1", {}, "response1")
        cache.set("prompt2", {}, "response2")
        cache.set("prompt3", {}, "response3")
        
        # Agregar cuarto elemento, debe evict el más antiguo (prompt1)
        cache.set("prompt4", {}, "response4")
        
        assert cache.get("prompt1", {}) is None
        assert cache.get("prompt2", {}) == "response2"
        assert cache.get("prompt3", {}) == "response3"
        assert cache.get("prompt4", {}) == "response4"
    
    def test_cache_lru_access_updates_order(self):
        """Validar acceso actualiza orden LRU"""
        cache = LLMCache(max_size=3, default_ttl=60)
        
        cache.set("prompt1", {}, "response1")
        cache.set("prompt2", {}, "response2")
        cache.set("prompt3", {}, "response3")
        
        # Acceder prompt1 para hacerlo más reciente
        cache.get("prompt1", {})
        
        # Agregar cuarto, debe evict prompt2 (ahora el más antiguo)
        cache.set("prompt4", {}, "response4")
        
        assert cache.get("prompt1", {}) == "response1"
        assert cache.get("prompt2", {}) is None
        assert cache.get("prompt3", {}) == "response3"
        assert cache.get("prompt4", {}) == "response4"
    
    def test_cache_ttl_expiration(self):
        """Validar expiración por TTL"""
        cache = LLMCache(max_size=3, default_ttl=1)  # 1 segundo TTL
        
        cache.set("prompt", {}, "response")
        
        # Inmediatamente debe estar disponible
        assert cache.get("prompt", {}) == "response"
        
        # Esperar expiración
        time.sleep(1.1)
        
        # Debe estar expirado
        assert cache.get("prompt", {}) is None
    
    def test_cache_custom_ttl(self):
        """Validar TTL custom por entrada"""
        cache = LLMCache(max_size=3, default_ttl=60)
        
        # TTL custom de 1 segundo
        cache.set("prompt1", {}, "response1", ttl=1)
        cache.set("prompt2", {}, "response2", ttl=60)
        
        time.sleep(1.1)
        
        assert cache.get("prompt1", {}) is None
        assert cache.get("prompt2", {}) == "response2"
    
    def test_cache_clear(self):
        """Validar limpieza completa del cache"""
        cache = LLMCache(max_size=3, default_ttl=60)
        
        cache.set("prompt1", {}, "response1")
        cache.set("prompt2", {}, "response2")
        
        cache.clear()
        
        assert cache.get("prompt1", {}) is None
        assert cache.get("prompt2", {}) is None
    
    def test_cache_stats(self):
        """Validar estadísticas de cache"""
        cache = LLMCache(max_size=3, default_ttl=60)
        
        cache.set("prompt1", {}, "response1")
        cache.set("prompt2", {}, "response2")
        
        # Hits
        cache.get("prompt1", {})
        cache.get("prompt1", {})
        
        # Miss
        cache.get("prompt3", {})
        
        stats = cache.get_stats()
        
        assert stats["size"] == 2
        assert stats["max_size"] == 3
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(0.666, rel=0.01)
    
    def test_cache_overwrite_same_key(self):
        """Validar sobrescritura de misma key"""
        cache = LLMCache(max_size=3, default_ttl=60)
        
        cache.set("prompt", {}, "response1")
        cache.set("prompt", {}, "response2")
        
        # Solo debe haber una entrada
        stats = cache.get_stats()
        assert stats["size"] == 1
        
        # Debe retornar valor más reciente
        assert cache.get("prompt", {}) == "response2"
    
    def test_cache_hash_collision_resistance(self):
        """Validar resistencia a colisiones de hash"""
        cache = LLMCache(max_size=10, default_ttl=60)
        
        # Múltiples prompts similares
        prompts = [f"Test prompt {i}" for i in range(10)]
        
        for i, prompt in enumerate(prompts):
            cache.set(prompt, {}, f"response{i}")
        
        # Todos deben ser recuperables
        for i, prompt in enumerate(prompts):
            assert cache.get(prompt, {}) == f"response{i}"
