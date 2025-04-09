"""
Exceptions personnalisées pour le module d'authentification.

Ce module contient les exceptions spécifiques au module d'authentification.
"""
from fastapi import HTTPException, status

from src.auth.constants import (
    ERROR_CREDENTIALS_INVALID,
    ERROR_TOKEN_EXPIRED,
    ERROR_TOKEN_INVALID,
    ERROR_TOKEN_MISSING,
    ERROR_USER_INACTIVE,
    ERROR_USER_NOT_FOUND,
    ERROR_PERMISSION_DENIED,
    HEADER_WWW_AUTHENTICATE,
    HEADER_WWW_AUTHENTICATE_VALUE,
)

class InvalidCredentialsException(HTTPException):
    """Exception pour des identifiants de connexion invalides."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_CREDENTIALS_INVALID,
            headers={HEADER_WWW_AUTHENTICATE: HEADER_WWW_AUTHENTICATE_VALUE},
        )

class TokenExpiredException(HTTPException):
    """Exception pour un token JWT expiré."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_TOKEN_EXPIRED,
            headers={HEADER_WWW_AUTHENTICATE: HEADER_WWW_AUTHENTICATE_VALUE},
        )

class TokenInvalidException(HTTPException):
    """Exception pour un token JWT invalide."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_TOKEN_INVALID,
            headers={HEADER_WWW_AUTHENTICATE: HEADER_WWW_AUTHENTICATE_VALUE},
        )

class TokenMissingException(HTTPException):
    """Exception pour un token JWT manquant."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_TOKEN_MISSING,
            headers={HEADER_WWW_AUTHENTICATE: HEADER_WWW_AUTHENTICATE_VALUE},
        )

class InactiveUserException(HTTPException):
    """Exception pour un utilisateur inactif."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_USER_INACTIVE,
        )

class PermissionDeniedException(HTTPException):
    """Exception pour une permission refusée."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_PERMISSION_DENIED,
        ) 