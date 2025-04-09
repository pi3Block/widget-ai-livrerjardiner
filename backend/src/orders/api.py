import logging
from typing import List, Annotated

from fastapi import APIRouter, HTTPException, Depends, Query, status, Response

# Schemas
from src.orders.models import (
    OrderCreate, OrderResponse, OrderUpdate, PaginatedOrderResponse
)

# Services & Dependencies
from src.orders.application.services import OrderService
from src.orders.interfaces.dependencies import get_order_service

# Exceptions
from src.orders.domain.exceptions import (
    OrderNotFoundException, 
    OrderUpdateForbiddenException,
    InvalidOrderStatusException,
    OrderCreationFailedException,
    InsufficientStockForOrderException
)
from src.products.domain.exceptions import VariantNotFoundException, InsufficientStockException
from addresses.exceptions import AddressNotFoundException

# Auth & Models
from src.auth.security import get_current_active_user, get_current_admin_user
from src.users.models import UserRead as UserSchema
from src.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE  # Import des constantes de pagination

logger = logging.getLogger(__name__)

order_router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

# Alias pour CurrentUser
CurrentUser = Annotated[UserSchema, Depends(get_current_active_user)]
# Alias pour Admin
CurrentAdmin = Annotated[UserSchema, Depends(get_current_admin_user)]
# Alias pour la dépendance du service
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]

@order_router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order_endpoint(
    service: OrderServiceDep,
    current_user: CurrentUser,
    order_data: OrderCreate,
):
    """Crée une nouvelle commande pour l'utilisateur authentifié."""
    try:
        created_order = await service.create_order(
            order_data=order_data, 
            requesting_user_id=current_user.id
        )
        logger.info(f"Commande {created_order.id} créée avec succès pour l'utilisateur {current_user.id}.")
        return OrderResponse.model_validate(created_order)
    except (AddressNotFoundException, VariantNotFoundException, InsufficientStockException) as e:
        logger.warning(f"Échec création commande user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InvalidOrderStatusException as e:
        logger.error(f"Erreur opération invalide création commande user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur inattendue création commande user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

@order_router.get("/", response_model=PaginatedOrderResponse)
async def list_user_orders_endpoint(
    service: OrderServiceDep,
    current_user: CurrentUser,
    response: Response,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0)
):
    """Liste les commandes de l'utilisateur authentifié avec pagination."""
    try:
        orders, total_count = await service.list_user_orders(
            user_id=current_user.id, 
            limit=limit, 
            offset=offset
        )
        end_range = offset + len(orders) - 1 if orders else offset
        response.headers["Content-Range"] = f"orders {offset}-{end_range}/{total_count}"
        
        # Convertir les entités en réponses
        order_responses = [OrderResponse.model_validate(order) for order in orders]
        return PaginatedOrderResponse(items=order_responses, total=total_count)
    except Exception as e:
        logger.exception(f"Erreur listage commandes user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

@order_router.get("/{order_id}", response_model=OrderResponse)
async def get_order_details_endpoint(
    service: OrderServiceDep,
    current_user: CurrentUser,
    order_id: int,
):
    """Récupère les détails d'une commande spécifique si elle appartient à l'utilisateur."""
    try:
        order = await service.get_order(
            order_id=order_id, 
            user_id=current_user.id, 
            is_admin=False
        )
        if not order:
            logger.warning(f"Tentative accès non autorisé commande {order_id} par user {current_user.id}.")
            raise OrderNotFoundException(order_id=order_id)
        return OrderResponse.model_validate(order)
    except OrderNotFoundException as e:
        logger.debug(f"Commande {order_id} non trouvée ou non accessible pour user {current_user.id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur récupération commande {order_id} user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

@order_router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status_endpoint(
    service: OrderServiceDep,
    current_user: CurrentUser,
    order_id: int,
    status_update: OrderUpdate,
):
    """Met à jour le statut d'une commande (ex: ANNULE)."""
    try:
        updated_order = await service.update_order_status(
            order_id=order_id, 
            status=status_update.status, 
            requesting_user_id=current_user.id, 
            is_admin=False
        )
        logger.info(f"Statut commande {order_id} mis à jour à '{status_update.status}' par user {current_user.id}.")
        return OrderResponse.model_validate(updated_order)
    except OrderNotFoundException as e:
        logger.warning(f"Commande {order_id} non trouvée pour MAJ statut par user {current_user.id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (OrderUpdateForbiddenException, InvalidOrderStatusException) as e:
        logger.warning(f"Échec MAJ statut commande {order_id} par user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur inattendue MAJ statut commande {order_id} user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

# TODO: Ajouter un endpoint pour Admin pour lister/voir/modifier toutes les commandes 