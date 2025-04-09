"""
Fonctions utilitaires de sécurité pour l'authentification.

Comprend le hachage/vérification de mot de passe et la création/décodage de token JWT.
"""
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import logging

# Importer la configuration du module
from src.auth.config import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

logger = logging.getLogger(__name__)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe en clair contre un hash bcrypt."""
    try:
        plain_password_bytes = plain_password.encode('utf-8')
        hashed_password_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du mot de passe: {e}", exc_info=True)
        return False

def get_password_hash(password: str) -> str:
    """Génère le hash bcrypt d'un mot de passe."""
    try:
        password_bytes = password.encode('utf-8')
        hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        return hashed_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Erreur lors du hachage du mot de passe: {e}", exc_info=True)
        # Il est généralement préférable de lever une exception ici
        raise ValueError("Erreur lors du hachage du mot de passe")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crée un token JWT avec les données fournies et une expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[int]:
    """Décode un token JWT et retourne l'ID utilisateur ('sub') ou None si invalide/expiré."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            logger.warning("Token JWT décodé mais sans champ 'sub' (user_id).")
            return None
        try:
            return int(user_id_str)
        except ValueError:
            logger.warning(f"Le champ 'sub' dans le token n'est pas un entier valide: '{user_id_str}'")
            return None
    except JWTError as e:
        logger.warning(f"Erreur de décodage JWT: {e}") # Inclut expiration, signature invalide, etc.
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue lors du décodage du token JWT: {e}", exc_info=True)
        return None 