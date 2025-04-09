# src/orders/repositories.py
import logging
from typing import List, Optional, Tuple, Dict, Any

from fastcrud import FastCRUD, NotFoundError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.orders.interfaces.repositories import AbstractOrderRepository
from src.orders.models import Order, OrderCreate, OrderUpdate, OrderRead, OrderItem, OrderItemCreate
from src.orders.exceptions import OrderCreationFailedException, OrderNotFoundException # Import specific exceptions

logger = logging.getLogger(__name__)


class SQLAlchemyOrderRepository(AbstractOrderRepository):
    """Implémentation SQLAlchemy du repository des commandes avec FastCRUD et gestion des relations."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        # CRUD pour Order (utilisé pour les opérations simples)
        self.crud_order = FastCRUD[Order, OrderCreate, OrderUpdate, OrderUpdate, OrderRead, OrderRead](Order)
        # CRUD pour OrderItem (utilisé pour la création en masse)
        self.crud_item = FastCRUD[OrderItem, OrderItemCreate, Dict[str, Any], Dict[str, Any], None, None](OrderItem)

    async def get_by_id(self, order_id: int) -> Optional[Order]:
        logger.debug(f"[OrderRepository] Getting order (ORM) by ID: {order_id}")
        try:
            # Utilise schema_to_select=None pour obtenir l'ORM
            order = await self.crud_order.get(db=self.db, id=order_id, schema_to_select=None)
            if not order:
                 logger.warning(f"[OrderRepository] Order (ORM) not found by ID: {order_id}")
            return order
        except NotFoundError:
            logger.warning(f"[OrderRepository] Order (ORM) not found by ID {order_id} (FastCRUD NotFoundError)")
            return None
        except Exception as e:
             logger.error(f"[OrderRepository] Error getting order {order_id}: {e}", exc_info=True)
             raise

    async def get_by_id_as_read_schema(self, order_id: int) -> Optional[OrderRead]:
        logger.debug(f"[OrderRepository] Getting order (Read Schema) by ID: {order_id}")
        # Utiliser une requête SQLAlchemy directe pour charger les relations
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items), # Charger les lignes de commande
                selectinload(Order.delivery_address), # Charger l'adresse de livraison
                selectinload(Order.billing_address) # Charger l'adresse de facturation
            )
        )
        result = await self.db.execute(stmt)
        order_orm = result.scalars().first()

        if not order_orm:
            logger.warning(f"[OrderRepository] Order not found by ID: {order_id} for Read Schema")
            return None
        
        # Convertir l'ORM en schéma Read (qui devrait gérer les relations chargées)
        return OrderRead.model_validate(order_orm)

    async def list_by_user(self, user_id: int, limit: int, offset: int) -> Tuple[List[OrderRead], int]:
        logger.debug(f"[OrderRepository] Listing orders for user ID: {user_id}, limit={limit}, offset={offset}")
        # Utiliser get_multi avec count pour la pagination et charger les relations
        result = await self.crud_order.get_multi(
            db=self.db,
            offset=offset,
            limit=limit,
            schema_to_select=OrderRead, # On veut le schéma Read directement
            filters={"user_id": user_id},
            sort_columns=["order_date"],
            sort_orders=["desc"],
            options=[ # Options pour charger les relations
                 selectinload(Order.items),
                 selectinload(Order.delivery_address),
                 selectinload(Order.billing_address)
            ]
        )
        return result.get('data', []), result.get('total', 0)

    async def create_order_with_items(
        self, 
        order_data: Dict[str, Any],
        items_data: List[Dict[str, Any]]
    ) -> Order:
        logger.debug(f"[OrderRepository] Creating order for user {order_data.get('user_id')}")
        # Pas besoin de transaction explicite ici si la session est gérée par FastAPI
        # Mais si des opérations externes (stock) sont faites ici, une transaction serait nécessaire.
        try:
            # 1. Créer l'Order
            # Note: FastCRUD create retourne l'ORM, pas besoin de schema_to_select ici
            created_order = await self.crud_order.create(db=self.db, object=order_data)
            await self.db.flush() # Pour obtenir l'ID de la commande créée

            # 2. Préparer et créer les OrderItems
            items_to_create = []
            for item in items_data:
                item["order_id"] = created_order.id # Assigner l'ID de la commande
                items_to_create.append(item)
            
            # Utiliser bulk_create pour l'efficacité
            if items_to_create:
                await self.crud_item.bulk_create(db=self.db, objects=items_to_create)
            
            await self.db.flush()
            await self.db.refresh(created_order, attribute_names=['items']) # Recharger la relation items

            logger.info(f"[OrderRepository] Order ID {created_order.id} created with {len(items_to_create)} items.")
            return created_order

        except Exception as e:
            await self.db.rollback()
            logger.error(f"[OrderRepository] Error creating order with items: {e}", exc_info=True)
            raise OrderCreationFailedException(f"Database error during order creation: {e}")

    async def update_order_status(self, order_id: int, status: str) -> Optional[Order]:
        logger.debug(f"[OrderRepository] Updating status for order ID: {order_id} to '{status}'")
        try:
            # Utiliser update de FastCRUD, retourne l'ORM mis à jour
            updated_order = await self.crud_order.update(
                db=self.db,
                object={"status": status},
                id=order_id,
                schema_to_select=None # On veut l'ORM
            )
            await self.db.flush()
            await self.db.refresh(updated_order)
            return updated_order
        except NotFoundError:
            logger.warning(f"[OrderRepository] Order not found for status update: ID {order_id}")
            raise OrderNotFoundException(order_id=order_id)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"[OrderRepository] Error updating status for order {order_id}: {e}", exc_info=True)
            raise

    # Implémenter d'autres méthodes de l'interface si définies 