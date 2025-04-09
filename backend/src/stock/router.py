import logging
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path

# Import des dépendances et services
from stock.service import StockService
from .dependencies import get_stock_service
from src.auth.security import get_current_admin_user # Pour protéger certaines routes
from src.users.interfaces import user_api_schemas as user_schemas # Pour typer l'utilisateur admin

# Import des schémas API Stock
from stock.models import StockRead, StockUpdate # Schémas de base
from stock.service import PaginatedStockResponse # Schéma de pagination déplacé dans service.py

# Import des exceptions
from src.products.domain.exceptions import StockNotFoundException, InsufficientStockException

logger = logging.getLogger(__name__)

# Création du routeur API pour le stock
router = APIRouter(
    prefix="/stock",
    tags=["Stock"], # Tag pour la documentation Swagger/OpenAPI
    # dependencies=[Depends(get_current_admin_user)] # Protéger toutes les routes par défaut si nécessaire
)

# Type hint pour l'injection du service
StockServiceDep = Annotated[StockService, Depends(get_stock_service)]
AdminUserDep = Annotated[user_schemas.User, Depends(get_current_admin_user)]

# --- Endpoints API --- 

@router.get(
    "/low", 
    response_model=PaginatedStockResponse, 
    summary="Lister les articles avec peu de stock",
    dependencies=[Depends(get_current_admin_user)] # Route protégée pour admin
)
async def list_low_stock(
    stock_service: StockServiceDep,
    threshold: int = Query(10, ge=0, title="Seuil de stock bas", description="Lister les articles dont le stock est <= à ce seuil"),
    limit: int = Query(50, ge=1, le=200, title="Limite d'éléments par page"),
    offset: int = Query(0, ge=0, title="Offset pour la pagination")
):
    """Récupère une liste paginée des articles dont le stock est inférieur ou égal au seuil spécifié."""
    logger.info(f"[API Stock] Requête list_low_stock avec seuil={threshold}, limit={limit}, offset={offset}")
    try:
        paginated_result = await stock_service.list_low_stock_variants(threshold=threshold, limit=limit, offset=offset)
        return paginated_result
    except Exception as e:
        logger.exception(f"[API Stock] Erreur lors du listage du stock bas: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération du stock bas.")

@router.get(
    "/{product_variant_id}", 
    response_model=StockRead,
    summary="Obtenir le stock d'une variante spécifique"
    # Protection admin peut être ajoutée si nécessaire: dependencies=[Depends(get_current_admin_user)]
)
async def get_variant_stock(
    product_variant_id: int = Path(..., title="ID de la Variante Produit", ge=1),
    stock_service: StockServiceDep = Depends(get_stock_service)
):
    """Récupère les informations de stock pour une variante de produit spécifique par son ID."""
    logger.info(f"[API Stock] Requête get_variant_stock pour ID: {product_variant_id}")
    stock_info = await stock_service.get_stock_for_variant(product_variant_id=product_variant_id)
    if stock_info is None:
        logger.warning(f"[API Stock] Stock non trouvé pour variante ID: {product_variant_id}")
        raise HTTPException(status_code=404, detail=f"Stock non trouvé pour la variante produit ID {product_variant_id}.")
    return stock_info

@router.patch(
    "/{product_variant_id}", 
    response_model=StockRead,
    summary="Mettre à jour le stock ou le seuil d'alerte",
    dependencies=[Depends(get_current_admin_user)] # Route protégée pour admin
)
async def update_variant_stock_details(
    product_variant_id: int = Path(..., title="ID de la Variante Produit", ge=1),
    stock_update_data: StockUpdate = Depends(), # Utiliser Depends() pour les données du corps PATCH
    stock_service: StockServiceDep = Depends(get_stock_service)
):
    """Met à jour la quantité et/ou le seuil d'alerte pour une variante de produit.
       Seuls les champs fournis dans le corps de la requête seront mis à jour.
    """
    logger.info(f"[API Stock] Requête update_variant_stock_details pour ID: {product_variant_id} avec données: {stock_update_data.model_dump(exclude_unset=True)}")
    
    # Vérifier qu'au moins une donnée est fournie pour la mise à jour
    if stock_update_data.model_dump(exclude_unset=True) == {}:
        raise HTTPException(status_code=400, detail="Aucune donnée fournie pour la mise à jour du stock.")
        
    try:
        updated_stock = await stock_service.update_stock_details(
            product_variant_id=product_variant_id, 
            stock_update=stock_update_data
        )
        return updated_stock
    except StockNotFoundException as e:
        logger.warning(f"[API Stock] Stock non trouvé pour MAJ détails, variante ID: {product_variant_id}")
        raise HTTPException(status_code=404, detail=f"Stock non trouvé pour la variante produit ID {e.variant_id}.")
    except ValueError as ve:
         logger.warning(f"[API Stock] Données invalides pour MAJ stock variante {product_variant_id}: {ve}")
         raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"[API Stock] Erreur lors de la mise à jour des détails du stock pour variante {product_variant_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne lors de la mise à jour des détails du stock.")

# Note: Pas d'endpoint POST pour créer directement une entrée Stock via API.
# La création initiale du stock devrait être gérée lors de la création de la variante produit
# (soit automatiquement via trigger/hook, soit par un appel à StockService dans ProductService).

# Note: Pas d'endpoint DELETE pour supprimer une entrée Stock via API.
# La suppression devrait être gérée lors de la suppression de la variante produit (via CASCADE ou hook). 