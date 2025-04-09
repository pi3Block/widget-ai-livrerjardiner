"""
Module définissant les routes API FastAPI pour l'authentification.

Contient les endpoints pour:
- /token : Connexion et obtention d'un token JWT
- /me : Récupération des informations de l'utilisateur connecté
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

# Importations locales
from src.auth.dependencies import get_auth_service, get_current_active_user
from src.auth.models import Token
from src.auth.security import create_access_token
from src.auth.service import AuthService
from src.auth.constants import ERROR_CREDENTIALS_INVALID, HEADER_WWW_AUTHENTICATE, HEADER_WWW_AUTHENTICATE_VALUE

# Importation du modèle utilisateur
from src.users.models import UserRead

logger = logging.getLogger(__name__)

# Définition du routeur
router = APIRouter()

@router.post("/token", response_model=Token, tags=["Authentication"])
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """
    Authentifie l'utilisateur et retourne un token JWT.
    
    - **username**: Email de l'utilisateur (utilisé comme identifiant)
    - **password**: Mot de passe de l'utilisateur
    """
    logger.info("[Router] Tentative de login pour: %s", form_data.username)
    
    # AuthService retourne le modèle ORM User ou None
    user = await auth_service.authenticate_user(email=form_data.username, password=form_data.password)
    if not user:
        logger.warning("[Router] Échec authentification pour: %s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_CREDENTIALS_INVALID,
            headers={HEADER_WWW_AUTHENTICATE: HEADER_WWW_AUTHENTICATE_VALUE},
        )

    # Créer le token en utilisant la fonction de sécurité
    access_token = create_access_token(data={"sub": str(user.id)})
    logger.info("[Router] Token créé pour user ID: %s", user.id)
    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=UserRead, tags=["Authentication"])
async def read_users_me(
    current_user: Annotated[UserRead, Depends(get_current_active_user)]
):
    """
    Récupère les informations de l'utilisateur actuellement connecté.
    
    Nécessite un token JWT valide dans l'en-tête Authorization.
    """
    logger.info("[Router] Récupération infos pour user ID: %s", current_user.id)
    return current_user

# Créer une instance du routeur pour l'export
auth_router = router 