"""
Configuration pour le module de gestion des utilisateurs.
"""
from pydantic_settings import BaseSettings

class UserSettings(BaseSettings):
    """Paramètres de configuration pour la gestion des utilisateurs."""
    
    # Paramètres de base de données
    USER_TABLE_NAME: str = "users"
    USER_ROLE_TABLE_NAME: str = "user_roles"
    
    # Paramètres de sécurité
    JWT_SECRET_KEY: str = "your-secret-key"  # À remplacer par une vraie clé secrète
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Paramètres de validation
    EMAIL_VERIFICATION_REQUIRED: bool = True
    PASSWORD_RESET_ENABLED: bool = True
    
    # Paramètres de cache
    CACHE_TTL: int = 300  # 5 minutes
    CACHE_PREFIX: str = "user:"
    
    # Paramètres de pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_prefix = "USER_"
        case_sensitive = True

# Instance des paramètres
settings = UserSettings() 