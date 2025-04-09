"""
Configuration du module d'authentification.

Ce module contient les constantes et paramètres de configuration spécifiques à l'authentification.
"""
import os
from typing import Optional

# --- Configuration JWT ---
# Dans un environnement de production, ces valeurs devraient être chargées
# depuis des variables d'environnement ou un système de gestion de secrets.
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# --- Configuration OAuth2 ---
OAUTH2_TOKEN_URL: str = "/auth/token"
OAUTH2_SCHEME_NAME: str = "JWT" 