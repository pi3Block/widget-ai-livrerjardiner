"""
Configuration pour le module LLM.
"""
from pydantic_settings import BaseSettings

class LLMSettings(BaseSettings):
    """Paramètres de configuration pour le module LLM."""
    
    # Paramètres de base de données
    LLM_REQUEST_TABLE_NAME: str = "llm_requests"
    
    # Paramètres d'API
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    DEFAULT_MODEL: str = "gpt-3.5-turbo"
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 1000
    
    # Paramètres de cache
    CACHE_TTL: int = 3600  # 1 heure
    CACHE_PREFIX: str = "llm:"
    
    # Paramètres de rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 3600  # 1 heure
    
    # Paramètres de logging
    LOG_REQUESTS: bool = True
    LOG_RESPONSES: bool = True
    
    class Config:
        env_prefix = "LLM_"
        case_sensitive = True

# Instance des paramètres
settings = LLMSettings() 