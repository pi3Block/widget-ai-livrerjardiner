"""
Constantes pour le module d'authentification.

Ce module contient les constantes utilisées dans le module d'authentification.
"""

# --- Messages d'erreur ---
ERROR_CREDENTIALS_INVALID = "Email ou mot de passe incorrect"
ERROR_TOKEN_EXPIRED = "Token d'authentification expiré"
ERROR_TOKEN_INVALID = "Token d'authentification invalide"
ERROR_TOKEN_MISSING = "Token d'authentification manquant"
ERROR_USER_INACTIVE = "Compte utilisateur inactif"
ERROR_USER_NOT_FOUND = "Utilisateur non trouvé"
ERROR_PERMISSION_DENIED = "Permission refusée"

# --- En-têtes HTTP ---
HEADER_WWW_AUTHENTICATE = "WWW-Authenticate"
HEADER_WWW_AUTHENTICATE_VALUE = "Bearer" 