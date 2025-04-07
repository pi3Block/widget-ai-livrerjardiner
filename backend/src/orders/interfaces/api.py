import logging
from typing import List, Annotated

from fastapi import APIRouter, HTTPException, Depends, Query, status, Response

# Schemas
from src.orders.application.schemas import OrderCreate, OrderResponse, OrderUpdate, PaginatedOrderResponse

# Services & Dependencies
from src.orders.application.services import OrderService
from src.orders.interfaces.dependencies import OrderServiceDep

# Exceptions
from src.orders.domain.exceptions import (
    OrderNotFoundException, 
    OrderUpdateForbiddenException,
    InvalidOrderStatusException,
    OrderCreationFailedException,
    InsufficientStockForOrderException
)
from src.products.domain.exceptions import VariantNotFoundException, InsufficientStockException
from src.addresses.domain.exceptions import AddressNotFoundException

# Auth & Models
from src.core.security import get_current_active_user_entity
from src.database import models
from src.users.domain.user_entity import UserEntity

logger = logging.getLogger(__name__)

order_router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)

# Alias pour CurrentUser
CurrentUser = Annotated[UserEntity, Depends(get_current_active_user_entity)]

@order_router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order_endpoint(
    order_data: OrderCreate,
    service: OrderServiceDep,
    current_user: CurrentUser,
):
    """Crée une nouvelle commande pour l'utilisateur authentifié."""
    try:
        # Associer la commande à l'utilisateur actuel
        created_order = await service.create_order(user_id=current_user.id, order_data=order_data)
        logger.info(f"Commande {created_order.id} créée avec succès pour l'utilisateur {current_user.id}.")
        return created_order
    except (AddressNotFoundException, VariantNotFoundException, InsufficientStockException) as e:
        logger.warning(f"Échec création commande user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InvalidOrderStatusException as e:
        logger.error(f"Erreur opération invalide création commande user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur inattendue création commande user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

@order_router.get("/", response_model=List[OrderResponse])
async def list_user_orders_endpoint(
    response: Response,
    service: OrderServiceDep,
    current_user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Liste les commandes de l'utilisateur authentifié avec pagination."""
    try:
        orders, total_count = await service.list_orders_for_user(user_id=current_user.id, limit=limit, offset=offset)
        end_range = offset + len(orders) - 1 if orders else offset
        response.headers["Content-Range"] = f"orders {offset}-{end_range}/{total_count}"
        return orders
    except Exception as e:
        logger.exception(f"Erreur listage commandes user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

@order_router.get("/{order_id}", response_model=OrderResponse)
async def get_order_details_endpoint(
    order_id: int,
    service: OrderServiceDep,
    current_user: CurrentUser,
):
    """Récupère les détails d'une commande spécifique si elle appartient à l'utilisateur."""
    try:
        order = await service.get_order_details(order_id=order_id)
        if not order or order.user_id != current_user.id:
             logger.warning(f"Tentative accès non autorisé commande {order_id} par user {current_user.id}.")
             raise OrderNotFoundException(order_id=order_id) # Simuler not found pour non autorisé
        return order
    except OrderNotFoundException as e:
        logger.debug(f"Commande {order_id} non trouvée ou non accessible pour user {current_user.id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur récupération commande {order_id} user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

@order_router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status_endpoint(
    order_id: int,
    status_update: OrderUpdate, # On utilise un schema même si un seul champ pour extensibilité
    service: OrderServiceDep,
    current_user: CurrentUser, # Pourrait être réservé aux admins
):
    """Met à jour le statut d'une commande (ex: ANNULE).
    TODO: Ajouter une vérification de rôle (admin/utilisateur).
    Actuellement, seul l'utilisateur propriétaire peut (potentiellement) annuler.
    """
    try:
        # Vérification initiale si la commande appartient à l'utilisateur
        order_check = await service.get_order_details(order_id=order_id)
        if not order_check or order_check.user_id != current_user.id:
             logger.warning(f"Tentative MAJ statut non autorisé commande {order_id} par user {current_user.id}.")
             raise OrderNotFoundException(order_id=order_id)

        # Logique de mise à jour du statut via le service
        updated_order = await service.update_order_status(order_id=order_id, new_status=status_update.status, user_id=current_user.id)
        logger.info(f"Statut commande {order_id} mis à jour à '{status_update.status}' par user {current_user.id}.")
        return updated_order
    except OrderNotFoundException as e:
        logger.warning(f"Commande {order_id} non trouvée pour MAJ statut par user {current_user.id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (OrderUpdateForbiddenException, InvalidOrderStatusException) as e:
        logger.warning(f"Échec MAJ statut commande {order_id} par user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur inattendue MAJ statut commande {order_id} user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.") 