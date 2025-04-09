"""
Configuration pour le module de gestion des stocks.
"""
from pydantic_settings import BaseSettings

class StockSettings(BaseSettings):
    """Paramètres de configuration pour la gestion des stocks."""
    
    # Paramètres de base de données
    STOCK_TABLE_NAME: str = "stock"
    STOCK_MOVEMENT_TABLE_NAME: str = "stock_movement"
    
    # Paramètres de cache
    CACHE_TTL: int = 300  # 5 minutes
    CACHE_PREFIX: str = "stock:"
    
    # Paramètres de notification
    ENABLE_STOCK_ALERTS: bool = True
    ALERT_EMAIL_RECIPIENTS: list[str] = []
    
    # Paramètres de pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_prefix = "STOCK_"
        case_sensitive = True

# Instance des paramètres
settings = StockSettings() 