import os
from dotenv import load_dotenv
import logging
from pydantic_settings import BaseSettings
from typing import Optional, List

logger = logging.getLogger(__name__)

# Charger les variables d'environnement AVANT de définir la classe Settings
load_dotenv()

# Classe de configuration utilisant Pydantic BaseSettings
class Settings(BaseSettings):
    # --- SMTP ---
    SENDER_EMAIL: str = "robotia@livrerjardiner.fr"
    SENDER_PASSWORD: str
    SMTP_HOST: str = "smtp.hostinger.com"
    SMTP_PORT: int = 465

    # --- Pagination ---
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100

    # --- Base de Données ---
    POSTGRES_DB: str = "livrerjardiner"
    POSTGRES_USER: str = "monuser"
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "192.168.1.13"
    POSTGRES_PORT: str = "5432"
    DB_ECHO_LOG: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # --- LLM / Ollama ---
    META_MODEL_NAME: str = "llama3"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    AVAILABLE_MODELS: dict = {
        "mistral": "mistral:latest",
        "llama3": "llama3:latest",
    }
    DEFAULT_MODEL: str = "mistral"

    # --- Application URLs ---
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"
    API_V1_PREFIX: str = "/api/v1" # Ajouter le préfixe API s'il est constant

    # --- JWT ---
    JWT_SECRET_KEY: str = "remplacer_par_une_vraie_cle_secrete_forte"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # --- Messages Génériques ---
    DB_CONNECT_ERROR_MSG: str = "Connexion à la base de données impossible pour le moment. Veuillez réessayer."
    DB_SQL_ERROR_MSG: str = "Un problème technique est survenu avec la base de données."
    LLM_ERROR_MSG: str = "Désolé, notre assistant IA rencontre un problème technique."
    FUNNY_ERROR_MESSAGES: List[str] = [
        "Oups, on dirait que nos rosiers ont pris des vacances ! Réessaie dans un instant.",
        "Aïe, le jardinier a trébuché sur un câble... On répare ça vite !",
        "Le stock a décidé de jouer à cache-cache. Patience, on le retrouve !",
        "Erreur 404 : Rosiers introuvables... ou peut-être qu'ils se sont enfuis ?",
        "Notre base de données fait la sieste. On la réveille avec un café !",
    ]

    class Config:
        # Charger depuis les variables d'environnement (respecte load_dotenv)
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignorer les variables d'env non définies dans le modèle

# Instancier la classe de configuration
settings = Settings()

# --- Log de confirmation et validation (après création de l'instance) ---

# Validation des secrets essentiels après le chargement
# Pydantic BaseSettings lèvera une erreur si des champs requis (ex: SENDER_PASSWORD) manquent
try:
    # Tentative d'accès aux champs requis pour forcer la validation de Pydantic
    _ = settings.SENDER_PASSWORD
    _ = settings.POSTGRES_PASSWORD
    _ = settings.JWT_SECRET_KEY
    if settings.JWT_SECRET_KEY == "remplacer_par_une_vraie_cle_secrete_forte":
         logger.warning("La variable JWT_SECRET_KEY utilise la valeur par défaut. Veuillez définir une clé secrète forte.")

except ValueError as e:
    logger.critical(f"Erreur de configuration: {e}")
    # Optionnel: lever l'exception pour arrêter l'application si la config est invalide
    # raise ValueError(f"Erreur de configuration: {e}")

logger.info(f"Configuration chargée: DB={settings.POSTGRES_DB}@{settings.POSTGRES_HOST}, Sender={settings.SENDER_EMAIL}, LLM URL={settings.OLLAMA_BASE_URL}")

# --- Supprimer les anciennes variables globales pour éviter la confusion ---
# (Optionnel mais recommandé pour la clarté)
# del SENDER_EMAIL, SENDER_PASSWORD, SMTP_HOST, SMTP_PORT # etc.

# Vous pouvez maintenant importer 'settings' depuis src.config
# from src.config import settings
# print(settings.POSTGRES_USER)
