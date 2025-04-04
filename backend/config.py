import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Charger les variables d'environnement au moment de l'import du module
load_dotenv()

# --- Configuration SMTP ---
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "robotia@livrerjardiner.fr")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD") # Pas de défaut
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.hostinger.com")
SMTP_PORT_STR = os.getenv("SMTP_PORT", "465")

# --- Configuration Base de Données ---
POSTGRES_DB = os.getenv("POSTGRES_DB", "livrerjardiner")
POSTGRES_USER = os.getenv("POSTGRES_USER", "monuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD") # Pas de défaut
# POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost") # Ajouter si différent de localhost
# POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")     # Ajouter si différent de 5432

# --- Configuration LLM ---
# Nom du modèle Meta (LLaMA) à utiliser via Ollama
META_MODEL_NAME = os.getenv("META_MODEL_NAME", "llama3") # Ex: "llama3", "llama2", etc.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# --- Validation et Conversion ---

# Valider les mots de passe manquants
if SENDER_PASSWORD is None:
    logger.critical("La variable d'environnement SENDER_PASSWORD n'est pas définie!")
    # raise ValueError("SENDER_PASSWORD doit être défini")

if POSTGRES_PASSWORD is None:
    logger.critical("La variable d'environnement POSTGRES_PASSWORD n'est pas définie!")
    # raise ValueError("POSTGRES_PASSWORD doit être défini")

# Convertir le port SMTP en entier
SMTP_PORT = 465 # Valeur par défaut si conversion échoue
try:
    SMTP_PORT = int(SMTP_PORT_STR)
except (ValueError, TypeError):
    logger.warning(f"Impossible de convertir SMTP_PORT ('{SMTP_PORT_STR}') en entier. Utilisation de la valeur par défaut {SMTP_PORT}.")

# Log de la configuration chargée (sauf mots de passe)
logger.info(f"Config chargée: SENDER_EMAIL={SENDER_EMAIL}, SMTP_HOST={SMTP_HOST}, SMTP_PORT={SMTP_PORT}")
logger.info(f"Config chargée: POSTGRES_DB={POSTGRES_DB}, POSTGRES_USER={POSTGRES_USER}")
logger.info(f"Config LLM: META_MODEL_NAME={META_MODEL_NAME}, OLLAMA_BASE_URL={OLLAMA_BASE_URL}")

# Optionnel: Exposer comme un dictionnaire ou une classe
# class Settings:
#     SENDER_EMAIL: str = SENDER_EMAIL
#     # ... autres variables ...
# settings = Settings()
