"""
Utilitaires pour le module de gestion des utilisateurs.
"""
import re
from datetime import datetime, timedelta
from typing import Optional

from .constants import (
    MIN_PASSWORD_LENGTH,
    MAX_PASSWORD_LENGTH,
    PASSWORD_RESET_TIMEOUT,
    USER_STATUS_ACTIVE,
    USER_STATUS_INACTIVE,
    USER_STATUS_SUSPENDED,
    USER_STATUS_DELETED
)

def validate_email(email: str) -> bool:
    """
    Valide le format d'un email.
    
    Args:
        email: Email à valider
        
    Returns:
        bool: True si l'email est valide, False sinon
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password: str) -> bool:
    """
    Valide un mot de passe selon les règles de sécurité.
    
    Args:
        password: Mot de passe à valider
        
    Returns:
        bool: True si le mot de passe est valide, False sinon
    """
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        return False
    
    # Vérifie la présence d'au moins une majuscule, une minuscule, un chiffre
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    
    return all([has_upper, has_lower, has_digit, has_special])

def generate_password_reset_token(user_id: int, timestamp: Optional[datetime] = None) -> str:
    """
    Génère un token de réinitialisation de mot de passe.
    
    Args:
        user_id: ID de l'utilisateur
        timestamp: Horodatage (optionnel)
        
    Returns:
        str: Token formaté
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    expiry = timestamp + timedelta(seconds=PASSWORD_RESET_TIMEOUT)
    return f"reset-{user_id}-{expiry.strftime('%Y%m%d%H%M%S')}"

def is_account_active(status: str) -> bool:
    """
    Vérifie si un compte est actif.
    
    Args:
        status: Statut du compte
        
    Returns:
        bool: True si le compte est actif, False sinon
    """
    return status == USER_STATUS_ACTIVE

def format_user_reference(user_id: int, timestamp: Optional[datetime] = None) -> str:
    """
    Génère une référence unique pour un utilisateur.
    
    Args:
        user_id: ID de l'utilisateur
        timestamp: Horodatage (optionnel)
        
    Returns:
        str: Référence formatée
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    return f"USR-{user_id:06d}-{timestamp.strftime('%Y%m%d')}" 