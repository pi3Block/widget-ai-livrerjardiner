"""
Module définissant les modèles SQLModel pour l'authentification.

Ce module contient :
- TokenData : Schéma pour les données contenues dans le token JWT.
- Token : Schéma pour la réponse du token d'accès.
"""
from typing import Optional

from sqlmodel import SQLModel

# =====================================================
# Schémas: Authentification (Token)
# =====================================================

class TokenData(SQLModel):
    """Schéma pour les données contenues dans le token JWT."""
    user_id: Optional[int] = None

class Token(SQLModel):
    """Schéma pour la réponse du token d'accès."""
    access_token: str
    token_type: str 