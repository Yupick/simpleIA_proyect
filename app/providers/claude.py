"""
Claude Provider - Integración con Anthropic API.
"""
import httpx
from typing import Optional
from .base import BaseLLMProvider


class ClaudeProvider(BaseLLMProvider):
    """Provider para modelos Claude de Anthropic."""
    
    def __init__(self, api_key: str, model_name: str = "claude-3-sonnet-20240229"):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.api_version = "2023-06-01"
    
    def generate(
        self,
        prompt: str,
        max_length: int = 100,
        num_return_sequences: int = 1,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Genera texto usando Claude API.
        
        Args:
            prompt: Texto de entrada
            max_length: Tokens máximos (se mapea a max_tokens)
            num_return_sequences: Ignorado (Claude no soporta múltiples secuencias)
            temperature: Control de aleatoriedad (0.0-1.0)
        
        Returns:
            Texto generado por Claude
        """
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "max_tokens": max_length,
            "temperature": min(max(temperature, 0.0), 1.0),
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.base_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                # Extraer texto de la respuesta
                if "content" in data and len(data["content"]) > 0:
                    return data["content"][0]["text"]
                return "[ERROR] Respuesta vacía de Claude"
                
        except httpx.HTTPStatusError as e:
            return f"[ERROR] Claude API error {e.response.status_code}: {e.response.text}"
        except httpx.RequestError as e:
            return f"[ERROR] Error de conexión con Claude: {str(e)}"
        except Exception as e:
            return f"[ERROR] Error inesperado en Claude provider: {str(e)}"
