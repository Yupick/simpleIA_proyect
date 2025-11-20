"""
Pydantic Settings - Configuración centralizada y validada con variables de entorno.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    """Configuración de la aplicación con validación Pydantic."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Seguridad
    SECRET_KEY: str = "CHANGE_ME"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 30
    
    # Modelo
    DEFAULT_MODEL: str = "gpt2"
    NUM_TRAIN_EPOCHS: int = 3
    TRAIN_BATCH_SIZE: int = 4
    DEVICE: str = "cpu"
    PROVIDER: str = "hf"
    
    # API
    CORS_ORIGINS: List[str] = ["http://localhost:8001"]
    
    # Entorno
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    # Proveedores externos (opcionales)
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None


# Instancia global de configuración
settings = Settings()
