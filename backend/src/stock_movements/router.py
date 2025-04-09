import logging
from typing import List, Optional, Annotated, Tuple

from fastapi import APIRouter, Depends, Query, Path, HTTPException, status

# Importer le service et les dépendances
from .service import StockMovementService, PaginatedStockMovementResponse
from .dependencies import StockMovementServiceDep

# Importer les modèles/schémas
from .models import StockMovementRead, StockMovementCreate # Create n'est pas utilisé dans ce routeur initial

# Importer les exceptions
from .exceptions import (
    StockMovementNotFoundException,
    InvalidStockMovementOperationException
)

# Core dependencies (pour Admin/Auth)
from src.auth.security import get_current_admin_user
from src.users.models import UserRead

logger = logging.getLogger(__name__)

# Dépendances Auth
AdminUserDep = Annotated[UserRead, Depends(get_current_admin_user)]

# --- Router Definition ---
router = APIRouter(
    # prefix="/stock-movements", # Préfixe défini dans main.py
    tags=["Stock Movements"] # Tag pour Swagger UI
)

# --- Pagination Helper --- (Factoriser dans un module partagé?)
def get_pagination_params(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Tuple[int, int]:
    return limit, offset

PaginationParams = Annotated[Tuple[int, int], Depends(get_pagination_params)]

# --- Error Handling Helper ---
def handle_stock_movement_service_errors(e: Exception):
    if isinstance(e, StockMovementNotFoundException):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    elif isinstance(e, InvalidStockMovementOperationException):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    else:
        logger.error(f"[StockMovement API] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error processing stock movement request.")

# --- Stock Movement Endpoints --- #

@router.get("/", response_model=PaginatedStockMovementResponse, dependencies=[Depends(get_current_admin_user)])
async def list_stock_movements(
    service: StockMovementServiceDep,
    pagination: PaginationParams = Depends(get_pagination_params),
    # Filtres optionnels
    product_variant_id: Optional[int] = Query(None, description="Filtrer par ID de variation produit"),
    movement_type: Optional[str] = Query(None, description="Filtrer par type de mouvement (ex: order_fulfillment, restock)"),
    order_item_id: Optional[int] = Query(None, description="Filtrer par ID d'item de commande lié")
):
    """Liste les mouvements de stock avec filtres et pagination (Admin requis)."""
    limit, offset = pagination
    logger.info(f"API list_stock_movements: limit={limit}, offset={offset}, variant={product_variant_id}, type={movement_type}, order_item={order_item_id}")
    try:
        paginated_result = await service.list_movements(
            limit=limit,
            offset=offset,
            product_variant_id=product_variant_id,
            movement_type=movement_type,
            order_item_id=order_item_id
            # Ajouter sort_by/sort_desc si nécessaire
        )
        return paginated_result
    except Exception as e:
        handle_stock_movement_service_errors(e)

@router.get("/{movement_id}", response_model=StockMovementRead, dependencies=[Depends(get_current_admin_user)])
async def read_stock_movement(
    service: StockMovementServiceDep,
    movement_id: int = Path(..., ge=1)
):
    """Récupère un mouvement de stock spécifique par son ID (Admin requis)."""
    logger.info(f"API read_stock_movement: ID={movement_id}")
    try:
        movement = await service.get_movement(movement_id=movement_id)
        return movement
    except Exception as e:
        handle_stock_movement_service_errors(e)

# Pas d'endpoint POST/PUT/DELETE ici car les mouvements sont généralement immuables
# et créés par d'autres processus (commandes, ajustements de stock via StockService). 