import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

# Import des services applicatifs via dépendances
from src.users.application.services import AuthService, UserService
from src.users.interfaces.dependencies import get_auth_service, get_user_service

# Import des schémas API
from src.users.interfaces import user_api_schemas as schemas

# Import des fonctions de sécurité applicative (pour créer le token)
from src.users.application import security

# Import de l'entité domaine (pour typer la dépendance de sécurité)
from src.users.domain.user_entity import UserEntity

# --- Importer la vraie dépendance de sécurité depuis core --- 
from src.core.security import get_current_active_user_entity
# --- Fin Import --- 

# --- Placeholder pour la dépendance de sécurité --- 
# Il faudra créer cette dépendance dans core/security.py ou users/interface/dependencies.py
# Elle devrait utiliser decode_access_token et le UserService/Repo pour retourner UserEntity
# async def get_current_active_user_entity() -> UserEntity: # Placeholder
#     # Implémentation réelle utilisera le token et les services
#     raise NotImplementedError("Dépendance get_current_active_user_entity non implémentée")
# --- Fin Placeholder ---

logger = logging.getLogger(__name__)

# Routeur pour l'authentification
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# Routeur pour les utilisateurs
user_router = APIRouter(prefix="/users", tags=["Users"])

# --- Routes d'Authentification ---

@auth_router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    logger.info(f"[Router] Tentative de login pour: {form_data.username}")
    user = await auth_service.authenticate_user(email=form_data.username, password=form_data.password)
    if not user:
        logger.warning(f"[Router] Échec authentification pour: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Créer le token en utilisant la fonction de sécurité
    # Le "sub" (subject) contient l'ID utilisateur
    access_token = security.create_access_token(data={"sub": str(user.id)})
    logger.info(f"[Router] Token créé pour user ID: {user.id}")
    return schemas.Token(access_token=access_token, token_type="bearer")

# --- Routes Utilisateur ---

@user_router.post("/", response_model=schemas.UserBase, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: schemas.UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    logger.info(f"[Router] Tentative d'enregistrement pour: {user_in.email}")
    try:
        # Le service s'occupe de la logique de création (check email, hashage via repo)
        created_user_entity = await user_service.create_user(
            email=user_in.email,
            password=user_in.password, # Passe le mot de passe en clair au service
            name=user_in.name
            # is_admin n'est pas dans UserCreate, donc False par défaut dans le service/repo
        )
        # Mapper l'entité retournée vers le schéma API pour la réponse
        # Note: UserBase ne contient pas is_admin, created_at, etc. C'est ok.
        return schemas.UserBase(
            email=created_user_entity.email,
            name=created_user_entity.name
        )
    except HTTPException as e:
        # Re-lever les exceptions HTTP (ex: 409 Conflict)
        raise e
    except Exception as e:
        logger.error(f"[Router] Erreur inattendue lors de l'enregistrement de {user_in.email}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la création de l'utilisateur.")

@user_router.get("/me", response_model=schemas.User)
async def read_users_me(
    # Utilise la vraie dépendance importée
    current_user: Annotated[UserEntity, Depends(get_current_active_user_entity)] 
):
    """Récupère les informations de l'utilisateur actuellement connecté."""
    logger.info(f"[Router] Récupération infos pour user ID: {current_user.id}")
    # L'entité UserEntity contient déjà les informations nécessaires.
    # Il faut juste la mapper vers le schéma API `schemas.User`.
    # Attention: UserEntity n'a pas de champ `addresses` direct.
    # La dépendance get_current_active_user_entity devra potentiellement charger 
    # les adresses séparément si le schéma `schemas.User` les requiert.
    # Pour l'instant, on retourne sans les adresses.
    return schemas.User(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        addresses=[] # Retourne une liste vide pour l'instant
    )

# Les routes pour /users/me/addresses/... restent dans main.py pour le moment.
