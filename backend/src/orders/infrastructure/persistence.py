import logging
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy import select, func, update as sqlalchemy_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload

# Modèles SQLAlchemy (depuis nouvel emplacement)
from src.database import models

# Domaine Orders
from src.orders.domain.entities import Order, OrderItem
from src.orders.domain.repositories import AbstractOrderRepository
from src.orders.domain.exceptions import OrderNotFoundException

from src.database.models import OrderDB, OrderItemDB, ProductVariantDB, StockMovementDB

logger = logging.getLogger(__name__)

class SQLAlchemyOrderRepository(AbstractOrderRepository):
    """Implémentation SQLAlchemy du repository de Commandes."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, order_id: int) -> Optional[Order]:
        """Récupère une commande par son ID, incluant ses items et potentiellement adresses."""
        stmt = select(models.OrderDB).where(models.OrderDB.id == order_id)
        stmt = stmt.options(
            selectinload(models.OrderDB.items).selectinload(models.OrderItemDB.product_variant), # Charger variante via item
            selectinload(models.OrderDB.delivery_address),
            selectinload(models.OrderDB.billing_address)
            # selectinload(models.OrderDB.user) # Charger si besoin
        )
        result = await self.session.execute(stmt)
        order_db = result.scalar_one_or_none()
        
        if not order_db:
            logger.debug(f"Commande ID {order_id} non trouvée dans get_by_id().")
            return None
        
        return Order.model_validate(order_db)

    async def list_for_user(self, user_id: int, limit: int, offset: int) -> List[Order]:
        """Liste les commandes pour un utilisateur donné avec pagination."""
        stmt = (
            select(models.OrderDB)
            .where(models.OrderDB.user_id == user_id)
            .options(selectinload(models.OrderDB.items)) # Charger items
            .order_by(models.OrderDB.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        orders_db = result.scalars().all()
        return [Order.model_validate(o_db) for o_db in orders_db]

    async def add(self, order_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Order:
        """Ajoute une nouvelle commande avec ses items.
        NOTE: La décrémentation du stock n'est PAS gérée ici.
        """
        new_order_db = models.OrderDB(**order_data)
        self.session.add(new_order_db)
        
        new_order_db.items = [models.OrderItemDB(**item) for item in items_data]
        
        try:
            await self.session.flush() # Obtenir ID et vérifier contraintes
            await self.session.refresh(new_order_db, attribute_names=['items', 'delivery_address', 'billing_address']) # Charger relations
            logger.info(f"Commande ID {new_order_db.id} ajoutée pour user {new_order_db.user_id}.")
            return Order.model_validate(new_order_db)
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erreur intégrité ajout commande pour user {order_data.get('user_id')}: {e}", exc_info=True)
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue ajout commande pour user {order_data.get('user_id')}: {e}", exc_info=True)
            raise

    async def update_status(self, order_id: int, status: str) -> Optional[Order]:
        """Met à jour le statut d'une commande."""
        order_db = await self.session.get(models.OrderDB, order_id)
        if not order_db:
            logger.warning(f"Tentative MAJ statut commande ID {order_id} non trouvée.")
            return None

        if order_db.status == status:
             logger.info(f"Statut commande {order_id} déjà '{status}'. Aucune MAJ nécessaire.")
             await self.session.refresh(order_db, attribute_names=['items', 'delivery_address', 'billing_address'])
             return Order.model_validate(order_db) 

        order_db.status = status
        
        try:
            await self.session.flush()
            await self.session.refresh(order_db, attribute_names=['items', 'delivery_address', 'billing_address'])
            logger.info(f"Statut commande ID {order_id} mis à jour à '{status}'.")
            return Order.model_validate(order_db)
        except Exception as e:
             await self.session.rollback()
             logger.error(f"Erreur inattendue MAJ statut commande {order_id}: {e}", exc_info=True)
             raise 