"""
Configuration du module addresses.
"""
from pydantic_settings import BaseSettings
from typing import Optional

class AddressSettings(BaseSettings):
    """
    Configuration pour le module addresses.
    
    Attributes:
        GEOCODING_API_KEY: Clé API pour le service de géocodage
        GEOCODING_API_URL: URL de l'API de géocodage
        CACHE_TTL: Durée de vie du cache en secondes
        MAX_RETRIES: Nombre maximum de tentatives pour les appels API
    """
    GEOCODING_API_KEY: Optional[str] = None
    GEOCODING_API_URL: str = "https://api-adresse.data.gouv.fr/search/"
    CACHE_TTL: int = 3600  # 1 heure
    MAX_RETRIES: int = 3

    class Config:
        env_prefix = "ADDRESS_"
        case_sensitive = True

# Instance de configuration
settings = AddressSettings() 