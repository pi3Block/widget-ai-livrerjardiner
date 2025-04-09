import logging
from typing import Optional, List, Annotated, Tuple, Dict, Any
import json

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body, Response

# Importer le service et les schémas/modèles
from .service import ProductVariantService #, PaginatedVariantResponse
from .models import ProductVariantRead, ProductVariantCreate, ProductVariantUpdate, ProductVariantReadWithStockAndTags
from .dependencies import VariantServiceDep # Dépendance du service

# Importer les exceptions spécifiques aux variations et celles des services dépendants
from .exceptions import VariantNotFoundException, DuplicateSKUException
from src.products.exceptions import ProductNotFoundException
from src.stock.exceptions import StockNotFoundException, StockUpdateFailedException
from src.tags.exceptions import TagNotFoundException

# Dépendances Core et Utilisateur
from src.auth.security import get_current_admin_user, get_current_active_user
from src.users.models import UserRead

logger = logging.getLogger(__name__)

# Dépendances Auth
AdminUserDep = Annotated[UserRead, Depends(get_current_admin_user)]
CurrentUserDep = Annotated[UserRead, Depends(get_current_active_user)]

# --- Router Definition ---
# Utiliser un préfixe clair, par exemple /products/{product_id}/variants ou /product-variants
# Choisissons /product-variants pour un routeur dédié
variant_router = APIRouter(
    prefix="/product-variants", # Préfixe pour toutes les routes de variations
    tags=["Product Variants"]
)

# --- Helper React-Admin (Copier si besoin) ---
def get_pagination_params(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
) -> Tuple[int, int]:
    return limit, offset

PaginationParams = Annotated[Tuple[int, int], Depends(get_pagination_params)]

# --- Helper Error Handling (Adapter) ---
def handle_variant_service_errors(e: Exception):
    if isinstance(e, (VariantNotFoundException, ProductNotFoundException, TagNotFoundException, StockNotFoundException)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    elif isinstance(e, DuplicateSKUException):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    # Ajouter la gestion d'autres exceptions spécifiques si nécessaire
    elif isinstance(e, Exception):
        logger.error(f"[Variant API] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error processing variant request.")
    else:
         logger.error(f"[Variant API] Non-exception error: {e}", exc_info=True)
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


# --- Variant Endpoints (/product-variants) ---

# Note: Lister toutes les variations sans filtre produit peut être lourd.
# Garder la liste par produit dans le routeur products?
# Ou ajouter un endpoint ici avec filtre product_id optionnel.
# Exemple: Lister les variations (potentiellement filtrées)
@variant_router.get("",
                    response_model=List[ProductVariantReadWithStockAndTags], # Ou PaginatedVariantResponse
                    summary="Lister les variations de produits (filtrage optionnel)")
async def list_variants(
    service: VariantServiceDep,
    pagination: PaginationParams,
    product_id: Optional[int] = Query(None, description="Filtrer par ID de produit")
):
    limit, offset = pagination
    logger.info(f"API list_variants: limit={limit}, offset={offset}, product_id={product_id}")
    try:
        if product_id:
            paginated_result = await service.list_variants_for_product(product_id=product_id, limit=limit, offset=offset)
            return paginated_result.items # Assumer le retour d'un objet paginé
        else:
            # Implémenter la liste de toutes les variations dans le service si nécessaire
            # paginated_result = await service.list_all_variants(limit=limit, offset=offset)
            # return paginated_result.items
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Listing all variants without product ID not implemented yet.")
    except Exception as e:
        handle_variant_service_errors(e)


# Endpoint pour créer une variation (besoin de product_id dans le body)
@variant_router.post("",
                     response_model=ProductVariantReadWithStockAndTags,
                     status_code=status.HTTP_201_CREATED,
                     summary="Créer une nouvelle variation de produit (Admin requis)",
                     dependencies=[Depends(get_current_admin_user)])
async def create_variant(
    service: VariantServiceDep,
    current_admin_user: AdminUserDep,
    variant_in: ProductVariantCreate # product_id est dans ce schéma
):
    logger.info(f"API create_variant by admin {current_admin_user.email}: SKU={variant_in.sku}, ProductID={variant_in.product_id}")
    try:
        # Le service gère la validation du product_id
        created_variant = await service.create_variant(variant_data=variant_in)
        return created_variant
    except Exception as e:
        handle_variant_service_errors(e)

@variant_router.get("/{variant_id}",
                    response_model=ProductVariantReadWithStockAndTags,
                    summary="Récupérer une variation par ID")
async def get_variant(
    service: VariantServiceDep,
    variant_id: int = Path(..., ge=1)
):
    logger.info(f"API get_variant: ID={variant_id}")
    try:
        variant = await service.get_variant(variant_id=variant_id)
        if variant is None:
             raise VariantNotFoundException(variant_id)
        return variant
    except Exception as e:
        handle_variant_service_errors(e)

@variant_router.put("/{variant_id}",
                    response_model=ProductVariantReadWithStockAndTags,
                    summary="Mettre à jour une variation (Admin requis)",
                    dependencies=[Depends(get_current_admin_user)])
async def update_variant(
    service: VariantServiceDep,
    current_admin_user: AdminUserDep,
    variant_id: int = Path(..., ge=1),
    variant_in: ProductVariantUpdate = Body(...)
):
    logger.info(f"API update_variant by admin {current_admin_user.email}: ID={variant_id}")
    try:
        updated_variant = await service.update_variant(variant_id=variant_id, variant_data=variant_in)
        if updated_variant is None:
             raise VariantNotFoundException(variant_id)
        return updated_variant
    except Exception as e:
        handle_variant_service_errors(e)

@variant_router.delete("/{variant_id}",
                       status_code=status.HTTP_204_NO_CONTENT,
                       summary="Supprimer une variation (Admin requis)",
                       dependencies=[Depends(get_current_admin_user)])
async def delete_variant(
    service: VariantServiceDep,
    current_admin_user: AdminUserDep,
    variant_id: int = Path(..., ge=1)
):
    logger.info(f"API delete_variant by admin {current_admin_user.email}: ID={variant_id}")
    try:
        deleted = await service.delete_variant(variant_id=variant_id)
        if not deleted:
            raise VariantNotFoundException(variant_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        handle_variant_service_errors(e)

# --- Routes spécifiques liées au stock pourraient aller ici ou dans un routeur de stock ---
# Exemple: (Déplacé de products/router)
# Note: Nécessite que VariantService ait des méthodes pour interagir avec StockService ou injecter StockService ici
# from src.stock.models import StockRead # Importer si nécessaire
# from src.stock.dependencies import StockServiceDep # Importer si nécessaire

# @variant_router.patch("/{variant_id}/stock",
#                      response_model=StockRead,
#                      summary="Ajuster la quantité de stock (Admin requis)",
#                      dependencies=[Depends(get_current_admin_user)])
# async def adjust_stock_for_variant(
#     # Injecter StockServiceDep ici au lieu de VariantServiceDep si la logique est dans StockService
#     stock_service: StockServiceDep,
#     current_admin_user: AdminUserDep,
#     variant_id: int = Path(..., ge=1),
#     quantity_change: int = Body(..., embed=True, description="Changement à appliquer au stock (peut être négatif)")
# ):
#     logger.info(f"API adjust_stock by admin {current_admin_user.email}: VariantID={variant_id}, Change={quantity_change}")
#     try:
#         # Assumer que StockService a une méthode `adjust_stock`
#         updated_stock = await stock_service.adjust_stock(variant_id, quantity_change)
#         if updated_stock is None:
#             raise VariantNotFoundException(variant_id) # Ou StockNotFoundException
#         return updated_stock
#     except Exception as e:
#         handle_variant_service_errors(e) # Utiliser un gestionnaire d'erreur adapté

# @variant_router.put("/{variant_id}/stock",
#                     response_model=StockRead,
#                     summary="Définir la quantité de stock absolue (Admin requis)",
#                     dependencies=[Depends(get_current_admin_user)])
# async def set_stock_for_variant(
#     stock_service: StockServiceDep,
#     current_admin_user: AdminUserDep,
#     variant_id: int = Path(..., ge=1),
#     new_quantity: int = Body(..., embed=True, ge=0, description="Nouvelle quantité de stock absolue")
# ):
#     logger.info(f"API set_stock by admin {current_admin_user.email}: VariantID={variant_id}, Quantity={new_quantity}")
#     try:
#         # Assumer que StockService a une méthode `set_stock`
#         updated_stock = await stock_service.set_stock(variant_id, new_quantity)
#         if updated_stock is None:
#              raise VariantNotFoundException(variant_id)
#         return updated_stock
#     except Exception as e:
#         handle_variant_service_errors(e) # Adapter la gestion d'erreur 