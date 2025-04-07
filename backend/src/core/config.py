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
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "192.168.1.13") # Ajouter si différent de localhost
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")     # Ajouter si différent de 5432

# Option pour afficher les logs SQL (True/False), défaut False
DB_ECHO_LOG = os.getenv("DB_ECHO_LOG", "False").lower() in ('true', '1', 't')

# Taille du pool de connexions et dépassement autorisé
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5")) # Nombre de connexions maintenues
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10")) # Connexions supplémentaires si pool plein

# --- Configuration LLM ---
# Nom du modèle Meta (LLaMA) à utiliser via Ollama
META_MODEL_NAME = os.getenv("META_MODEL_NAME", "llama3") # Ex: "llama3", "llama2", etc.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# --- Application URLs (Example) ---
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000") # Default to localhost

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

# Configuration Ollama (si nécessaire de spécifier l'URL)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Modèles LLM disponibles
AVAILABLE_MODELS = {
    "mistral": "mistral:latest",
    "llama3": "llama3:latest",
    # Ajouter d'autres modèles ici si nécessaire
}
DEFAULT_MODEL = "mistral" # Modèle à utiliser si non spécifié ou invalide

# Messages d'erreur génériques
DB_CONNECT_ERROR_MSG = "Connexion à la base de données impossible pour le moment. Veuillez réessayer."
DB_SQL_ERROR_MSG = "Un problème technique est survenu avec la base de données."
LLM_ERROR_MSG = "Désolé, notre assistant IA rencontre un problème technique."

# Liste de messages d'erreur "amusants" pour le frontend (peut être déplacée)
FUNNY_ERROR_MESSAGES = [
    "Oups, on dirait que nos rosiers ont pris des vacances ! Réessaie dans un instant.",
    "Aïe, le jardinier a trébuché sur un câble... On répare ça vite !",
    "Le stock a décidé de jouer à cache-cache. Patience, on le retrouve !",
    "Erreur 404 : Rosiers introuvables... ou peut-être qu'ils se sont enfuis ?",
    "Notre base de données fait la sieste. On la réveille avec un café !",
]

# Configuration JWT (JSON Web Token) pour l'authentification
# !!! IMPORTANT: Générer une clé secrète forte et la garder privée !!!
# Utiliser `openssl rand -hex 32` pour générer une clé sécurisée
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "remplacer_par_une_vraie_cle_secrete_forte")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Durée de validité du token en minutes

# Optionnel: Exposer comme un dictionnaire ou une classe
# class Settings:
#     SENDER_EMAIL: str = SENDER_EMAIL
#     # ... autres variables ...
# settings = Settings()
