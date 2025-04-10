"""
Constantes pour le module de gestion des utilisateurs.
"""

# Rôles utilisateur
ROLE_ADMIN = "ADMIN"
ROLE_MANAGER = "MANAGER"
ROLE_USER = "USER"
ROLE_GUEST = "GUEST"

# Statuts utilisateur
USER_STATUS_ACTIVE = "ACTIVE"
USER_STATUS_INACTIVE = "INACTIVE"
USER_STATUS_SUSPENDED = "SUSPENDED"
USER_STATUS_DELETED = "DELETED"

# Types de compte
ACCOUNT_TYPE_PERSONAL = "PERSONAL"
ACCOUNT_TYPE_PROFESSIONAL = "PROFESSIONAL"
ACCOUNT_TYPE_ASSOCIATION = "ASSOCIATION"

# Messages d'erreur
ERROR_USER_NOT_FOUND = "Utilisateur non trouvé"
ERROR_INVALID_CREDENTIALS = "Identifiants invalides"
ERROR_USER_ALREADY_EXISTS = "Un utilisateur avec cet email existe déjà"
ERROR_INVALID_ROLE = "Rôle invalide"
ERROR_ACCOUNT_DISABLED = "Compte désactivé"

# Limites
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MAX_LOGIN_ATTEMPTS = 5
PASSWORD_RESET_TIMEOUT = 3600  # 1 heure en secondes 