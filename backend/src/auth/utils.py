"""
Fonctions utilitaires pour le module d'authentification.

Ce module contient des fonctions ou classes auxiliaires qui ne rentrent pas
dans les autres catégories du module d'authentification.
"""
import logging
from typing import Optional, Dict, Any, List
import re

logger = logging.getLogger(__name__)

def extract_token_from_header(authorization_header: Optional[str]) -> Optional[str]:
    """
    Extrait le token JWT d'un en-tête Authorization.
    Exemple: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    Args:
        authorization_header: Valeur de l'en-tête Authorization
        
    Returns:
        Le token JWT extrait ou None si format invalide
    """
    if not authorization_header:
        return None
        
    match = re.match(r"Bearer\s+(.+)", authorization_header)
    if not match:
        logger.warning(f"Format d'en-tête Authorization invalide: {authorization_header}")
        return None
        
    return match.group(1) 