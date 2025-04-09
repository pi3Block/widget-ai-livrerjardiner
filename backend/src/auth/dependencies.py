"""
Module définissant les dépendances FastAPI pour l'authentification.

Fournit des dépendances pour:
- Le service d'authentification (AuthService)
- L'obtention de l'utilisateur courant à partir du token JWT
- La vérification des droits admin
"""
import logging
from typing import Annotated, Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

# Importations locales
from src.auth.service import AuthService
from src.auth.config import OAUTH2_TOKEN_URL
from src.auth.exceptions import TokenMissingException, TokenInvalidException, PermissionDeniedException

# Importation du modèle UserRead et de la DÉPENDANCE du repository utilisateur
from src.users.models import UserRead # User, UserCreate, UserUpdate ne sont plus nécessaires ici
from src.database import get_db_session
# IMPORTER LA DÉPENDANCE DU REPOSITORY UTILISATEUR
from src.users.dependencies import UserRepositoryDep
# Importer l'interface pour l'annotation de type
from src.users.interfaces.repositories import AbstractUserRepository

logger = logging.getLogger(__name__)

# --- Dépendances OAuth2 ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=OAUTH2_TOKEN_URL, auto_error=False)

# --- Dépendances de session DB ---
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

# --- Mettre à jour la dépendance pour obtenir le service d'authentification ---
# Elle dépend maintenant de UserRepositoryDep
def get_auth_service(
    # Injecter directement le repository via sa dépendance
    user_repository: UserRepositoryDep,
    # Supprimer db: DbSessionDep si AuthService ne l'utilise plus directement
) -> AuthService:
    """
    Fournit une instance du service d'authentification.
    
    Args:
        user_repository: Instance du repository utilisateur fournie par dépendance.
        
    Returns:
        AuthService: Instance du service d'authentification.
    """
    logger.debug("Fourniture de AuthService avec UserRepository injecté")
    # Passer le repository injecté au constructeur de AuthService
    return AuthService(user_repository=user_repository)

# --- Dépendances pour la vérification d'authentification ---
async def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    # Cette dépendance utilisera maintenant le AuthService correctement configuré
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> UserRead:
    """
    Vérifie le token JWT et retourne l'utilisateur courant.
    
    Args:
        token: Token JWT optionnel
        auth_service: Service d'authentification
        
    Returns:
        UserRead: Informations de l'utilisateur authentifié
        
    Raises:
        TokenMissingException: Si le token est manquant
        TokenInvalidException: Si le token est invalide
    """
    if token is None:
        logger.warning("Token manquant dans la requête.")
        raise TokenMissingException()

    # L'appel à auth_service.get_user_from_token utilisera le repository injecté
    user = await auth_service.get_user_from_token(token)
    if user is None:
        logger.warning("Token invalide ou utilisateur non trouvé.")
        raise TokenInvalidException()

    logger.debug(f"Utilisateur authentifié: ID {user.id}")
    return user

async def get_current_active_user(
    current_user: Annotated[UserRead, Depends(get_current_user)]
) -> UserRead:
    """
    Vérifie que l'utilisateur courant est actif.
    
    Args:
        current_user: Utilisateur courant
        
    Returns:
        UserRead: Informations de l'utilisateur actif
        
    Raises:
        InactiveUserException: Si l'utilisateur est inactif
    """
    # Si votre modèle User a un champ is_active, décommentez ce code
    # if not current_user.is_active:
    #     logger.warning(f"Tentative d'accès par un utilisateur inactif: ID {current_user.id}")
    #     raise InactiveUserException()
    return current_user

async def get_current_admin_user(
    current_user: Annotated[UserRead, Depends(get_current_active_user)]
) -> UserRead:
    """
    Vérifie que l'utilisateur courant est un administrateur.
    
    Args:
        current_user: Utilisateur courant
        
    Returns:
        UserRead: Informations de l'utilisateur administrateur
        
    Raises:
        PermissionDeniedException: Si l'utilisateur n'est pas administrateur
    """
    if not current_user.is_admin:
        logger.warning(f"Tentative d'accès à une ressource admin par un utilisateur non-admin: ID {current_user.id}")
        raise PermissionDeniedException()
    return current_user 