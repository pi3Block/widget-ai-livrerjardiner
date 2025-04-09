"""
Module définissant les routes API FastAPI pour les utilisateurs.

Contient les endpoints pour:
- /users/ : Enregistrement d'un nouvel utilisateur.
- /users/me : Récupération des informations de l'utilisateur connecté.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

# Import des dépendances locales
from src.users.dependencies import get_user_service
from src.users.service import UserService

# Import des modèles/schémas locaux
from src.users import models

# Import de la dépendance de sécurité du module auth (pour obtenir l'utilisateur courant)
from src.auth.dependencies import get_current_active_user

logger = logging.getLogger(__name__)

# Routeur principal pour ce module
router = APIRouter()

# --- Routes Utilisateur ---

@router.post("/", response_model=models.UserRead, status_code=status.HTTP_201_CREATED, tags=["Users"])
async def register_user(
    user_in: models.UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """Enregistre un nouvel utilisateur."""
    logger.info("[Router] Tentative d'enregistrement pour: %s", user_in.email)
    try:
        # Le service gère la vérification d'existence, le hachage et la création
        # et retourne directement le schéma UserRead
        created_user = await user_service.create_user(user_data=user_in)
        return created_user
    except HTTPException as e:
        # Re-lever les exceptions HTTP connues (ex: 409 Conflict)
        raise e
    except Exception as e:
        logger.error("[Router] Erreur inattendue lors de l'enregistrement de %s: %s", user_in.email, e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la création de l'utilisateur.")

@router.get("/me", response_model=models.UserRead, tags=["Users"])
async def read_users_me(
    # S'assurer que get_current_active_user retourne le bon type (models.UserRead)
    current_user: Annotated[models.UserRead, Depends(get_current_active_user)]
):
    """Récupère les informations de l'utilisateur actuellement connecté."""
    logger.info("[Router] Récupération infos pour user ID: %s", current_user.id)
    # La dépendance globale est supposée retourner directement le bon schéma
    return current_user

# Ajoutez d'autres endpoints utilisateur ici si nécessaire (GET /users/{id}, PUT /users/{id}, DELETE /users/{id})
# en utilisant le UserService et les dépendances appropriées (ex: get_user_service).

# Créer une instance du routeur pour l'export
user_router = router 