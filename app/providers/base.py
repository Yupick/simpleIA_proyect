from typing import Protocol

class BaseLLMProvider(Protocol):
    def generate(self, prompt: str, **kwargs) -> str:
        ...
