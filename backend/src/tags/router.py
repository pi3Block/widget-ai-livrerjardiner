import logging
from typing import Optional, List, Annotated, Tuple, Dict, Any
import json

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body, Response

# Importer le service et les schémas/modèles
from .service import TagService #, PaginatedTagResponse
from .models import TagRead, TagCreate, TagUpdate
from .dependencies import TagServiceDep # Dépendance du service

# Importer les exceptions
from .exceptions import TagNotFoundException, DuplicateTagNameException # Ajuster selon les exceptions définies

# Dépendances Core et Utilisateur
from src.auth.security import get_current_admin_user, get_current_active_user
from src.users.models import UserRead

logger = logging.getLogger(__name__)

# Dépendances Auth
AdminUserDep = Annotated[UserRead, Depends(get_current_admin_user)]
CurrentUserDep = Annotated[UserRead, Depends(get_current_active_user)]

# --- Router Definition ---
tag_router = APIRouter(
    prefix="/tags",
    tags=["Tags"]
)

# --- Helper React-Admin (Copier depuis products/router si besoin) ---
# Si vous utilisez les paramètres React-Admin, copiez la fonction
# parse_react_admin_params et la dépendance ReactAdminParams ici.
# Exemple simplifié sans React-Admin pour commencer:
def get_pagination_params(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Tuple[int, int]:
    return limit, offset

PaginationParams = Annotated[Tuple[int, int], Depends(get_pagination_params)]

# --- Helper Error Handling (Adapter) ---
def handle_tag_service_errors(e: Exception):
    if isinstance(e, TagNotFoundException):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    elif isinstance(e, DuplicateTagNameException): # Assumer cette exception
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    elif isinstance(e, Exception): # Gérer autres erreurs du service si nécessaire
        logger.error(f"[Tag API] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error processing tag request.")
    else:
         logger.error(f"[Tag API] Non-exception error: {e}", exc_info=True)
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

# --- Tag Endpoints (/tags) ---

@tag_router.get("",
                response_model=List[TagRead], # Ou PaginatedTagResponse si défini
                summary="Lister les tags")
async def list_tags(
    # response: Response, # Si utilisation des headers Content-Range
    service: TagServiceDep,
    pagination: PaginationParams # Utiliser la pagination simple
):
    limit, offset = pagination
    logger.info(f"API list_tags: limit={limit}, offset={offset}")
    try:
        # Adapter si le service retourne un objet paginé
        paginated_result = await service.list_tags(limit=limit, offset=offset)
        # Si PaginatedTagResponse:
        # response.headers["X-Total-Count"] = str(paginated_result.total)
        # return paginated_result.items
        return paginated_result.items # Supposons que list_tags retourne PaginatedTagResponse
    except Exception as e:
        handle_tag_service_errors(e)

@tag_router.post("",
                 response_model=TagRead,
                 status_code=status.HTTP_201_CREATED,
                 summary="Créer un nouveau tag (Admin requis)",
                 dependencies=[Depends(get_current_admin_user)])
async def create_tag(
    service: TagServiceDep,
    current_admin_user: AdminUserDep,
    tag_in: TagCreate
):
    logger.info(f"API create_tag by admin {current_admin_user.email}: name={tag_in.name}")
    try:
        created_tag = await service.create_tag(tag_data=tag_in)
        return created_tag
    except Exception as e:
        handle_tag_service_errors(e)

@tag_router.get("/{tag_id}",
                response_model=TagRead,
                summary="Récupérer un tag par ID")
async def get_tag(
    service: TagServiceDep,
    tag_id: int = Path(..., ge=1)
):
    logger.info(f"API get_tag: ID={tag_id}")
    try:
        tag = await service.get_tag(tag_id=tag_id)
        if tag is None:
             raise TagNotFoundException(tag_id)
        return tag
    except Exception as e:
        handle_tag_service_errors(e)

@tag_router.put("/{tag_id}",
                response_model=TagRead,
                summary="Mettre à jour un tag (Admin requis)",
                dependencies=[Depends(get_current_admin_user)])
async def update_tag(
    service: TagServiceDep,
    current_admin_user: AdminUserDep,
    tag_id: int = Path(..., ge=1),
    tag_in: TagUpdate = Body(...)
):
    logger.info(f"API update_tag by admin {current_admin_user.email}: ID={tag_id}")
    try:
        updated_tag = await service.update_tag(tag_id=tag_id, tag_data=tag_in)
        if updated_tag is None:
             raise TagNotFoundException(tag_id)
        return updated_tag
    except Exception as e:
        handle_tag_service_errors(e)

@tag_router.delete("/{tag_id}",
                   status_code=status.HTTP_204_NO_CONTENT,
                   summary="Supprimer un tag (Admin requis)",
                   dependencies=[Depends(get_current_admin_user)])
async def delete_tag(
    service: TagServiceDep,
    current_admin_user: AdminUserDep,
    tag_id: int = Path(..., ge=1)
):
    logger.info(f"API delete_tag by admin {current_admin_user.email}: ID={tag_id}")
    try:
        deleted = await service.delete_tag(tag_id=tag_id)
        if not deleted:
            raise TagNotFoundException(tag_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        handle_tag_service_errors(e) 