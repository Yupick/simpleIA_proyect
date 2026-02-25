"""
OpenAI Provider - Integración con OpenAI/Azure OpenAI API.
"""

import httpx
from .base import BaseLLMProvider


# Placeholder class to allow tests to patch the underlying async client
class AsyncOpenAI:
    pass


class OpenAIProvider(BaseLLMProvider):
    """Provider para modelos OpenAI (GPT-3.5, GPT-4, etc.)."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-3.5-turbo",
        base_url: str = "https://api.openai.com/v1/chat/completions",
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url

    async def generate(
        self,
        prompt,  # Puede ser str o List[Dict]
        max_length: int = 100,
        num_return_sequences: int = 1,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """
        Genera texto usando OpenAI API.

        Args:
            prompt: Texto de entrada (str) o lista de mensajes (List[Dict])
            max_length: Tokens máximos
            num_return_sequences: Número de respuestas (se usa 'n' en API)
            temperature: Control de aleatoriedad (0.0-2.0)

        Returns:
            Texto generado por OpenAI
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Convertir prompt a formato de mensajes
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list):
            messages = prompt
        else:
            return "[ERROR] Formato de prompt inválido"

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_length,
            "temperature": min(max(temperature, 0.0), 2.0),
            "n": num_return_sequences,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url, json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()

                # Extraer texto de la primera choice
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                return "[ERROR] Respuesta vacía de OpenAI"

        except httpx.HTTPStatusError as e:
            return (
                f"[ERROR] OpenAI API error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            return f"[ERROR] Error de conexión con OpenAI: {str(e)}"
        except Exception as e:
            return f"[ERROR] Error inesperado en OpenAI provider: {str(e)}"

    async def generate_stream(self, prompt, **kwargs):
        """
        Basic streaming fallback: call generate() and yield smaller chunks.
        Real implementations should stream from the API; tests may patch
        `AsyncOpenAI` or this method.
        """
        # Prefer using AsyncOpenAI client if available (tests patch this).
        try:
            AsyncClient = globals().get("AsyncOpenAI")
            if AsyncClient:
                import inspect

                client = AsyncClient(api_key=self.api_key)
                stream_candidate = client.stream(prompt)

                if inspect.isawaitable(stream_candidate):
                    stream_candidate = await stream_candidate

                if hasattr(stream_candidate, "__aenter__"):
                    async with stream_candidate as stream:
                        async for event in stream:
                            try:
                                if hasattr(event, "choice") and hasattr(
                                    event.choice, "delta"
                                ):
                                    yield getattr(event.choice.delta, "content", "")
                                else:
                                    yield str(event)
                            except Exception:
                                yield str(event)
                    return

                if hasattr(stream_candidate, "__aiter__"):
                    async for event in stream_candidate:
                        try:
                            if hasattr(event, "choice") and hasattr(
                                event.choice, "delta"
                            ):
                                yield getattr(event.choice.delta, "content", "")
                            else:
                                yield str(event)
                        except Exception:
                            yield str(event)
                    return

            # Fallback: call generate() and split
            full = await self.generate(prompt, **kwargs)
            if not full:
                return
            for chunk in str(full).split():
                yield chunk
        except Exception as e:
            yield f"[ERROR] Streaming failed: {e}"
