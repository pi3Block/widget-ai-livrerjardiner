import logging
from typing import Optional, List, Annotated, Tuple, Dict, Any
import json

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body, Response, Request
# Garder AsyncSession si utilisé par les dépendances injectées directement ici

# Dependencies: Importer ProductServiceDep et CategoryServiceDep
from .dependencies import ProductServiceDep, CategoryServiceDep # Ajuster si CategoryService a ses propres dépendances

# Service and Paginated Responses: Garder Product et Category
from .service import (
    # ProductService, # La classe n'est plus directement référencée ici
    PaginatedProductResponse, PaginatedCategoryResponse,
    # Supprimer PaginatedVariantResponse, PaginatedTagResponse
)

# Schemas: Garder Product et Category, importer les variations pour les réponses
from .models import (
    ProductRead, ProductCreate, ProductUpdate, ProductReadWithDetails, # Garder ProductReadWithDetails
    CategoryRead, CategoryCreate, CategoryUpdate,
    # Supprimer Variant et Tag schemas, importer VariantRead pour la réponse
    # ProductVariantRead, ProductVariantCreate, ProductVariantUpdate,
    # TagRead, TagCreate
)
from src.product_variants.models import ProductVariantReadWithStockAndTags # Pour ProductReadWithDetails

# Exceptions: Garder Product et Category, les autres sont gérées par les routeurs spécifiques
from .exceptions import (
    ProductNotFoundException, CategoryNotFoundException,
    ProductUpdateFailedException, ProductCreationFailedException,
    InvalidOperationException # Garder générique
    # Supprimer VariantNotFoundException, DuplicateSKUException, etc.
)

# Core dependencies
from src.auth.security import get_current_admin_user, get_current_active_user
from src.users.models import UserRead

logger = logging.getLogger(__name__)

# Auth Dependencies
AdminUserDep = Annotated[UserRead, Depends(get_current_admin_user)]
CurrentUserDep = Annotated[UserRead, Depends(get_current_active_user)]

# --- Router Definition (Garder Product et Category) ---
product_router = APIRouter(
    prefix="/products",
    tags=["Products"]
)

category_router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)

# Supprimer tag_router et variant_router d'ici

# --- React-Admin Parameter Parsing (Garder si utilisé pour Product/Category) ---
def parse_react_admin_params(
    filter: Optional[str] = Query(None, alias="filter"),
    range_param: Optional[str] = Query(None, alias="range"),
    sort: Optional[str] = Query(None, alias="sort")
) -> Tuple[int, int, Optional[str], bool, Optional[Dict[str, Any]]]:
    offset = 0
    limit = 100
    sort_by = None
    sort_desc = False
    filters = None
    # ... (même logique de parsing qu'avant)
    if range_param:
        try:
            range_list = json.loads(range_param)
            if isinstance(range_list, list) and len(range_list) == 2:
                offset = int(range_list[0])
                limit = int(range_list[1]) - offset + 1
                if limit <= 0: limit = 1
        except (json.JSONDecodeError, ValueError, IndexError):
            logger.warning(f"Invalid 'range' parameter: {range_param}. Using defaults.")
    if sort:
        try:
            sort_list = json.loads(sort)
            if isinstance(sort_list, list) and len(sort_list) == 2:
                sort_by = str(sort_list[0])
                sort_desc = str(sort_list[1]).upper() == 'DESC'
        except (json.JSONDecodeError, ValueError, IndexError):
            logger.warning(f"Invalid 'sort' parameter: {sort}. No sorting applied.")
    if filter:
        try:
            filters = json.loads(filter)
            if not isinstance(filters, dict):
                 logger.warning(f"Invalid 'filter' parameter (not a dict): {filter}. No filters applied.")
                 filters = None
        except json.JSONDecodeError:
            logger.warning(f"Invalid 'filter' parameter (not JSON): {filter}. No filters applied.")
            filters = None
    return limit, offset, sort_by, sort_desc, filters

ReactAdminParams = Annotated[Tuple[int, int, Optional[str], bool, Optional[Dict[str, Any]]], Depends(parse_react_admin_params)]

# --- Helper Function for Error Handling (Simplifié pour Product/Category) ---
def handle_product_category_service_errors(e: Exception):
    if isinstance(e, (ProductNotFoundException, CategoryNotFoundException)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    elif isinstance(e, InvalidOperationException): # Gérer les erreurs génériques du service
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    elif isinstance(e, (ProductUpdateFailedException, ProductCreationFailedException)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    else:
        logger.error(f"[Product/Category API] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred.")


# --- Category Endpoints (/categories) ---
# Ces routes utilisent maintenant CategoryServiceDep (à définir dans dependencies.py)

@category_router.get("",
                     response_model=List[CategoryRead],
                     summary="Lister les catégories (Compatible React-Admin)")
async def list_categories(
    response: Response,
    service: CategoryServiceDep, # Utiliser la dépendance du service Category
    ra_params: ReactAdminParams
):
    limit, offset, sort_by, sort_desc, filters = ra_params
    # Adapter l'appel au CategoryService
    logger.info(f"API list_categories: limit={limit}, offset={offset}, filters={filters}")
    try:
        # Assumer que CategoryService a une méthode list_categories compatible
        paginated_result = await service.list_categories(
            limit=limit, offset=offset # Ajouter sort/filters si supporté
        )
        total_count = paginated_result.total
        items = paginated_result.items
        end_range = offset + len(items) - 1 if items else offset
        response.headers["Content-Range"] = f"categories {offset}-{end_range}/{total_count}"
        response.headers["X-Total-Count"] = str(total_count)
        return items
    except Exception as e:
        handle_product_category_service_errors(e) # Utiliser le gestionnaire d'erreurs adapté

@category_router.get("/{category_id}",
                     response_model=CategoryRead,
                     summary="Récupérer une catégorie par ID")
async def get_category(
    service: CategoryServiceDep,
    category_id: int = Path(..., ge=1)
):
    logger.info(f"API get_category: ID={category_id}")
    try:
        category = await service.get_category(category_id=category_id)
        # Le service doit lever une exception si non trouvé
        if category is None: # Double vérification
             raise CategoryNotFoundException(category_id)
        return category
    except Exception as e:
        handle_product_category_service_errors(e)

@category_router.post("",
                      response_model=CategoryRead,
                      status_code=status.HTTP_201_CREATED,
                      summary="Créer une nouvelle catégorie (Admin requis)",
                      dependencies=[Depends(get_current_admin_user)])
async def create_category(
    service: CategoryServiceDep,
    current_admin_user: AdminUserDep,
    category_in: CategoryCreate
):
    logger.info(f"API create_category by admin {current_admin_user.email}: name={category_in.name}")
    try:
        created_category = await service.create_category(category_data=category_in)
        return created_category
    except Exception as e:
        handle_product_category_service_errors(e)

@category_router.put("/{category_id}",
                     response_model=CategoryRead,
                     summary="Mettre à jour une catégorie (Admin requis)",
                     dependencies=[Depends(get_current_admin_user)])
async def update_category(
    service: CategoryServiceDep,
    current_admin_user: AdminUserDep,
    category_id: int = Path(..., ge=1),
    category_in: CategoryUpdate = Body(...)
):
    logger.info(f"API update_category by admin {current_admin_user.email}: ID={category_id}")
    try:
        updated_category = await service.update_category(category_id=category_id, category_data=category_in)
        if updated_category is None:
             raise CategoryNotFoundException(category_id)
        return updated_category
    except Exception as e:
        handle_product_category_service_errors(e)

@category_router.delete("/{category_id}",
                        status_code=status.HTTP_204_NO_CONTENT,
                        summary="Supprimer une catégorie (Admin requis)",
                        dependencies=[Depends(get_current_admin_user)])
async def delete_category(
    service: CategoryServiceDep,
    current_admin_user: AdminUserDep,
    category_id: int = Path(..., ge=1)
):
    logger.info(f"API delete_category by admin {current_admin_user.email}: ID={category_id}")
    try:
        # Assumer que delete_category lève une exception si non trouvé ou échoue
        await service.delete_category(category_id=category_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        handle_product_category_service_errors(e)

# --- Product Endpoints (/products) ---
# Ces routes utilisent ProductServiceDep

@product_router.get("",
                    response_model=List[ProductReadWithDetails], # Réponse détaillée avec variations
                    summary="Lister les produits (Compatible React-Admin)")
async def list_products(
    response: Response,
    service: ProductServiceDep,
    ra_params: ReactAdminParams,
    # Les filtres spécifiques (category_id, search) sont gérés par le service maintenant
    category_id: Optional[int] = Query(None, description="Filtrer par ID de catégorie"),
    search: Optional[str] = Query(None, alias="q", description="Terme de recherche (nom, description)")
):
    limit, offset, sort_by, sort_desc, filters = ra_params
    # Combiner les filtres ra_params et les filtres spécifiques si nécessaire
    # ou passer les filtres spécifiques au service
    logger.info(f"API list_products: limit={limit}, offset={offset}, category={category_id}, search={search}, ra_filters={filters}")
    try:
        # Le service list_products retourne maintenant PaginatedProductResponse[ProductReadWithDetails]
        paginated_result: PaginatedProductResponse = await service.list_products(
            limit=limit, offset=offset, category_id=category_id, search_term=search # Ajouter sort/autres filtres si supporté
        )
        total_count = paginated_result.total
        items = paginated_result.items
        end_range = offset + len(items) - 1 if items else offset
        response.headers["Content-Range"] = f"products {offset}-{end_range}/{total_count}"
        response.headers["X-Total-Count"] = str(total_count)
        return items
    except Exception as e:
        handle_product_category_service_errors(e)

@product_router.get("/{product_id}",
                    response_model=ProductReadWithDetails, # Réponse détaillée
                    summary="Récupérer un produit par ID")
async def get_product(
    service: ProductServiceDep,
    product_id: int = Path(..., ge=1)
):
    logger.info(f"API get_product: ID={product_id}")
    try:
        # Le service get_product retourne maintenant ProductReadWithDetails
        product = await service.get_product(product_id=product_id)
        if product is None:
            raise ProductNotFoundException(product_id)
        return product
    except Exception as e:
        handle_product_category_service_errors(e)

@product_router.post("",
                     response_model=ProductReadWithDetails, # Retourne le produit créé détaillé
                     status_code=status.HTTP_201_CREATED,
                     summary="Créer un nouveau produit (Admin requis)",
                     dependencies=[Depends(get_current_admin_user)])
async def create_product(
    service: ProductServiceDep,
    current_admin_user: AdminUserDep,
    product_in: ProductCreate
):
    logger.info(f"API create_product by admin {current_admin_user.email}: name={product_in.name}")
    try:
        created_product = await service.create_product(product_data=product_in)
        return created_product
    except Exception as e:
        handle_product_category_service_errors(e)

@product_router.put("/{product_id}",
                    response_model=ProductReadWithDetails, # Retourne le produit mis à jour détaillé
                    summary="Mettre à jour un produit (Admin requis)",
                    dependencies=[Depends(get_current_admin_user)])
async def update_product(
    service: ProductServiceDep,
    current_admin_user: AdminUserDep,
    product_id: int = Path(..., ge=1),
    product_in: ProductUpdate = Body(...)
):
    logger.info(f"API update_product by admin {current_admin_user.email}: ID={product_id}")
    try:
        updated_product = await service.update_product(product_id=product_id, product_data=product_in)
        if updated_product is None:
            raise ProductNotFoundException(product_id)
        return updated_product
    except Exception as e:
        handle_product_category_service_errors(e)

@product_router.delete("/{product_id}",
                       status_code=status.HTTP_204_NO_CONTENT,
                       summary="Supprimer un produit (Admin requis)",
                       dependencies=[Depends(get_current_admin_user)])
async def delete_product(
    service: ProductServiceDep,
    current_admin_user: AdminUserDep,
    product_id: int = Path(..., ge=1)
):
    logger.info(f"API delete_product by admin {current_admin_user.email}: ID={product_id}")
    try:
        deleted = await service.delete_product(product_id=product_id)
        if not deleted:
            raise ProductNotFoundException(product_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        handle_product_category_service_errors(e)

# --- Les routes pour les variations (/products/{id}/variants, /variants/{id}, /variants/{id}/stock) sont SUPPRIMÉES ---
# --- Les routes pour les tags (/tags) sont SUPPRIMÉES --- 