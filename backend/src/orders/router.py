import logging
from typing import List, Annotated

from fastapi import APIRouter, HTTPException, Depends, Query, status, Response

# Schemas
from src.orders.models import (
    OrderCreate, OrderResponse, OrderUpdate, PaginatedOrderResponse
)

# Services & Dependencies
from src.orders.service import OrderService
from src.orders.dependencies import get_order_service

# Exceptions
from src.orders.exceptions import (
    OrderNotFoundException, 
    OrderUpdateForbiddenException,
    InvalidOrderStatusException,
    OrderCreationFailedException,
    InsufficientStockForOrderException
)
from src.products.exceptions import VariantNotFoundException, InsufficientStockException
from src.addresses.exceptions import AddressNotFoundException

# Auth & Models
from src.auth.dependencies import get_current_active_user, get_current_admin_user
from src.users.models import UserRead as UserSchema
from src.config import settings  # Import des constantes de pagination

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
    limit: int = Query(default=settings.DEFAULT_PAGE_SIZE, le=settings.MAX_PAGE_SIZE),
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

# Endpoints Admin
@order_router.get("/admin/all", response_model=PaginatedOrderResponse)
async def list_all_orders_endpoint(
    service: OrderServiceDep,
    current_admin: CurrentAdmin,
    response: Response,
    limit: int = Query(default=settings.DEFAULT_PAGE_SIZE, le=settings.MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0)
):
    """Liste toutes les commandes (endpoint admin)."""
    try:
        orders, total_count = await service.list_all_orders(
            limit=limit, 
            offset=offset
        )
        end_range = offset + len(orders) - 1 if orders else offset
        response.headers["Content-Range"] = f"orders {offset}-{end_range}/{total_count}"
        
        order_responses = [OrderResponse.model_validate(order) for order in orders]
        return PaginatedOrderResponse(items=order_responses, total=total_count)
    except Exception as e:
        logger.exception(f"Erreur listage commandes par admin {current_admin.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

@order_router.get("/admin/{order_id}", response_model=OrderResponse)
async def get_order_details_admin_endpoint(
    service: OrderServiceDep,
    current_admin: CurrentAdmin,
    order_id: int,
):
    """Récupère les détails d'une commande spécifique (endpoint admin)."""
    try:
        order = await service.get_order(
            order_id=order_id, 
            user_id=None, 
            is_admin=True
        )
        if not order:
            logger.warning(f"Commande {order_id} non trouvée par admin {current_admin.id}.")
            raise OrderNotFoundException(order_id=order_id)
        return OrderResponse.model_validate(order)
    except OrderNotFoundException as e:
        logger.debug(f"Commande {order_id} non trouvée pour admin {current_admin.id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur récupération commande {order_id} par admin {current_admin.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

@order_router.patch("/admin/{order_id}/status", response_model=OrderResponse)
async def update_order_status_admin_endpoint(
    service: OrderServiceDep,
    current_admin: CurrentAdmin,
    order_id: int,
    status_update: OrderUpdate,
):
    """Met à jour le statut d'une commande (endpoint admin)."""
    try:
        updated_order = await service.update_order_status(
            order_id=order_id, 
            status=status_update.status, 
            requesting_user_id=current_admin.id, 
            is_admin=True
        )
        logger.info(f"Statut commande {order_id} mis à jour à '{status_update.status}' par admin {current_admin.id}.")
        return OrderResponse.model_validate(updated_order)
    except OrderNotFoundException as e:
        logger.warning(f"Commande {order_id} non trouvée pour MAJ statut par admin {current_admin.id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (OrderUpdateForbiddenException, InvalidOrderStatusException) as e:
        logger.warning(f"Échec MAJ statut commande {order_id} par admin {current_admin.id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur inattendue MAJ statut commande {order_id} par admin {current_admin.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")
