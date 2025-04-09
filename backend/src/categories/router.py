import logging
from typing import List, Optional, Annotated, Tuple

from fastapi import APIRouter, Depends, Query, Path, Body, Response, HTTPException, status

# Importer le service et les dépendances
from .service import CategoryService, PaginatedCategoryResponse # Service refactorisé
from .dependencies import CategoryServiceDep # Dépendance du service

# Importer les modèles/schémas
from .models import CategoryRead, CategoryCreate, CategoryUpdate, CategoryReadWithDetails

# Importer les exceptions du service
from .exceptions import (
    CategoryNotFoundException,
    DuplicateCategoryNameException,
    CategoryUpdateFailedException,
    CategoryCreationFailedException,
    InvalidCategoryOperationException
)

# Core dependencies (pour Admin/Auth si nécessaire)
from src.auth.security import get_current_admin_user
from src.users.models import UserRead

logger = logging.getLogger(__name__)

# Dépendances Auth
AdminUserDep = Annotated[UserRead, Depends(get_current_admin_user)]

# --- Router Definition ---
router = APIRouter()

# --- Pagination Helper (Optionnel, ou utiliser React-Admin) ---
def get_pagination_params(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Tuple[int, int]:
    return limit, offset

PaginationParams = Annotated[Tuple[int, int], Depends(get_pagination_params)]

# --- Error Handling Helper ---
def handle_category_service_errors(e: Exception):
    if isinstance(e, CategoryNotFoundException):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    elif isinstance(e, DuplicateCategoryNameException):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    elif isinstance(e, (CategoryUpdateFailedException, CategoryCreationFailedException, InvalidCategoryOperationException)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    else:
        logger.error(f"[Category API] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error processing category request.")

# --- Category Endpoints --- #

@router.get("/categories/", response_model=PaginatedCategoryResponse)
async def read_categories(
    service: CategoryServiceDep,
    pagination: PaginationParams = Depends(get_pagination_params) # Utiliser la pagination simple
):
    """Récupère une liste paginée de catégories."""
    limit, offset = pagination
    logger.info(f"API read_categories: limit={limit}, offset={offset}")
    try:
        paginated_result = await service.list_categories(limit=limit, offset=offset)
        return paginated_result
    except Exception as e:
        handle_category_service_errors(e)

@router.post("/categories/", response_model=CategoryRead, status_code=201, dependencies=[Depends(get_current_admin_user)])
async def create_new_category(
    category: CategoryCreate,
    service: CategoryServiceDep,
    current_admin_user: AdminUserDep # Injecter l'admin pour le log
):
    """Crée une nouvelle catégorie (Admin requis)."""
    logger.info(f"API create_category by admin {current_admin_user.email}: name={category.name}")
    try:
        # La validation (nom unique, parent_id) est gérée par le service
        created_category = await service.create_category(category_data=category)
        return created_category
    except Exception as e:
        handle_category_service_errors(e)

@router.get("/categories/{category_id}", response_model=CategoryRead)
async def read_category(
    service: CategoryServiceDep,
    category_id: int = Path(..., ge=1)
):
    """Récupère une catégorie par son ID."""
    logger.info(f"API read_category: ID={category_id}")
    try:
        # Le service lève CategoryNotFoundException si non trouvé
        db_category = await service.get_category(category_id=category_id)
        return db_category
    except Exception as e:
        handle_category_service_errors(e)

# Endpoint potentiel pour les détails (si nécessaire)
# @router.get("/categories/{category_id}/details", response_model=CategoryReadWithDetails)
# async def read_category_with_details(...): ...

@router.put("/categories/{category_id}", response_model=CategoryRead, dependencies=[Depends(get_current_admin_user)])
async def update_existing_category(
    service: CategoryServiceDep,
    current_admin_user: AdminUserDep,
    category_id: int = Path(..., ge=1),
    category: CategoryUpdate = Body(...)
):
    """Met à jour une catégorie existante (Admin requis)."""
    logger.info(f"API update_category by admin {current_admin_user.email}: ID={category_id}")
    try:
        # La validation est gérée par le service
        updated_category = await service.update_category(category_id=category_id, category_data=category)
        return updated_category
    except Exception as e:
        handle_category_service_errors(e)

@router.delete("/categories/{category_id}", status_code=204, dependencies=[Depends(get_current_admin_user)])
async def delete_existing_category(
    service: CategoryServiceDep,
    current_admin_user: AdminUserDep,
    category_id: int = Path(..., ge=1)
):
    """Supprime une catégorie existante (Admin requis)."""
    logger.info(f"API delete_category by admin {current_admin_user.email}: ID={category_id}")
    try:
        # Le service lève CategoryNotFoundException si non trouvé
        await service.delete_category(category_id=category_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        handle_category_service_errors(e)