from threading import Lock
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Optional
import logging
import torch
import os

from ..core.config import config
from ..providers.huggingface import HuggingFaceProvider
from ..providers.claude import ClaudeProvider
from ..providers.openai import OpenAIProvider
from ..core.settings import settings

logger = logging.getLogger(__name__)

_model = None
_tokenizer = None
_current_model_name: Optional[str] = None
_provider_instance = None
_lock = Lock()

def get_device() -> torch.device:
    device_name = settings.DEVICE.lower()
    if device_name == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")

def load_model(force: bool = False):
    global _model, _tokenizer, _current_model_name, _provider_instance
    with _lock:
        if _provider_instance is not None and not force:
            return _current_model_name
        if _model is not None and not force:
            return _current_model_name
        model_name = config.selected_model
        provider = config.provider
        device = get_device()
        
        # Leer API keys y configuraciones adicionales desde config.json
        import json
        from pathlib import Path
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        config_path = BASE_DIR / "config" / "config.json"
        
        api_keys_config = {}
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    api_keys_config = json.load(f)
            except Exception as e:
                logger.warning(f"Error leyendo config.json: {e}")
        
        try:
            if provider == "hf":
                logger.info(f"[HF] Loading model: {model_name} on {device}")
                # Usar model_path si está disponible en config
                model_path = api_keys_config.get("model_path")
                if model_path and os.path.exists(model_path):
                    logger.info(f"[HF] Loading from local path: {model_path}")
                    model_to_load = model_path
                else:
                    model_to_load = model_name
                
                _tokenizer = AutoTokenizer.from_pretrained(model_to_load, clean_up_tokenization_spaces=True)
                _model = AutoModelForCausalLM.from_pretrained(model_to_load).to(device)
                
                # Crear instancia de HuggingFaceProvider para compatibilidad
                _provider_instance = HuggingFaceProvider(model_name=model_to_load, model=_model, tokenizer=_tokenizer)
            elif provider == "claude":
                api_key = api_keys_config.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    logger.error("[Claude] API key no encontrada en config.json ni en variables de entorno")
                    raise ValueError("Claude API key is required")
                
                logger.info(f"[Claude] Initializing Claude provider with model {model_name}")
                _provider_instance = ClaudeProvider(
                    api_key=api_key,
                    model_name=model_name or "claude-3-5-sonnet-20241022"
                )
                _model = None
                _tokenizer = None
            elif provider == "openai":
                api_key = api_keys_config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
                if not api_key:
                    logger.error("[OpenAI] API key no encontrada en config.json ni en variables de entorno")
                    raise ValueError("OpenAI API key is required")
                
                base_url = api_keys_config.get("openai_base_url", "https://api.openai.com/v1/chat/completions")
                logger.info(f"[OpenAI] Initializing OpenAI provider with model {model_name}")
                _provider_instance = OpenAIProvider(
                    api_key=api_key,
                    model_name=model_name or "gpt-3.5-turbo",
                    base_url=base_url
                )
                _model = None
                _tokenizer = None
            else:
                logger.warning(f"[Unknown provider:{provider}] Falling back to HuggingFaceProvider")
                _provider_instance = HuggingFaceProvider(model_name)
                _tokenizer = _provider_instance.tokenizer
                _model = _provider_instance.model.to(device)
            _current_model_name = model_name
            return _current_model_name
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            _model = None
            _tokenizer = None
            _provider_instance = None
            _current_model_name = None
            return None

async def generate(prompt: str, max_length: int = 50, num_return_sequences: int = 1, temperature: float = 0.7) -> str:
    # If using external provider (Claude, OpenAI), delegate to provider
    if _provider_instance is not None:
        try:
            return await _provider_instance.generate(prompt, max_length, num_return_sequences, temperature)
        except Exception as e:
            logger.error(f"Provider inference error: {e}")
            return f"[ERROR] Provider inference failed: {e}"
    
    # Local HuggingFace model inference
    if _model is None or _tokenizer is None:
        load_model()
    if _model is None:
        return "[ERROR] Modelo no cargado"
    if _tokenizer.pad_token_id is None:
        _tokenizer.pad_token = _tokenizer.eos_token
    device = get_device()
    try:
        enc = _tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
        input_ids = enc["input_ids"].to(device)
        attn = enc["attention_mask"].to(device)
        with torch.no_grad():
            out_ids = _model.generate(
                input_ids,
                attention_mask=attn,
                max_length=max_length,
                num_return_sequences=num_return_sequences,
                do_sample=True,
                temperature=temperature,
                pad_token_id=_tokenizer.pad_token_id
            )
        return _tokenizer.decode(out_ids[0], skip_special_tokens=True)
    except Exception as e:
        logger.error(f"Inference error: {e}")
        return "[ERROR] Falla en inferencia"

def current_model_name() -> Optional[str]:
    return _current_model_name
