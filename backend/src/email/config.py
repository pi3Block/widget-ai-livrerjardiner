from pydantic_settings import BaseSettings
from typing import Optional

class EmailSettings(BaseSettings):
    """Configuration du module email.
    
    Les paramètres sont chargés depuis les variables d'environnement avec le préfixe EMAIL_.
    """
    SMTP_HOST: str
    SMTP_PORT: int
    SENDER_EMAIL: str
    SENDER_PASSWORD: str
    USE_TLS: bool = True
    DEFAULT_FROM_NAME: Optional[str] = "LivrerJardiner"

    class Config:
        env_prefix = "EMAIL_"
        case_sensitive = True

# Instance globale des paramètres
settings = EmailSettings()
