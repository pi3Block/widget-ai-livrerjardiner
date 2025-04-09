import logging
from typing import List, Optional, TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select
from fastcrud import FastCRUD

# Import models and schemas
from .models import StockMovement, StockMovementCreate, StockMovementRead
# Importer les exceptions spécifiques
from .exceptions import (
    StockMovementNotFoundException,
    StockMovementCreationFailedException,
    InvalidStockMovementOperationException
)
# Importer les dépendances nécessaires pour la validation (si create est implémenté ici)
# from src.product_variants.exceptions import VariantNotFoundException
# from src.product_variants.dependencies import VariantCRUDDep # Exemple
# from src.orders.exceptions import OrderItemNotFoundException
# from src.orders.dependencies import OrderItemCRUDDep # Exemple

logger = logging.getLogger(__name__)

# --- Pagination Schema ---
T = TypeVar('T', bound=SQLModel)
class PaginatedResponse(SQLModel, Generic[T]):
    items: List[T]
    total: int
class PaginatedStockMovementResponse(PaginatedResponse[StockMovementRead]): pass
# ------------------------

class StockMovementService:
    """Service applicatif pour la gestion des mouvements de stock."""

    def __init__(self, db: AsyncSession, movement_crud: FastCRUD[StockMovement]):
        # Potentiellement injecter VariantCRUD, OrderItemCRUD si validation nécessaire
        self.db = db
        self.movement_crud = movement_crud
        logger.info("StockMovementService initialized.")

    async def list_movements(
        self,
        limit: int = 100,
        offset: int = 0,
        product_variant_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        order_item_id: Optional[int] = None,
        sort_by: str = "created_at", # Trier par date par défaut
        sort_desc: bool = True
    ) -> PaginatedStockMovementResponse:
        """Liste les mouvements de stock avec filtres et pagination."""
        filters = {}
        if product_variant_id is not None: filters["product_variant_id"] = product_variant_id
        if movement_type: filters["movement_type__ilike"] = f"%{movement_type}%"
        if order_item_id is not None: filters["order_item_id"] = order_item_id

        sort_column = f"-{sort_by}" if sort_desc else sort_by

        logger.debug(f"[StockMovementService] List Movements: filters={filters}, sort={sort_column}, limit={limit}, offset={offset}")
        try:
            movements, total_count = await self.movement_crud.get_multi(
                limit=limit,
                offset=offset,
                filters=filters,
                schema_to_select=StockMovementRead,
                sort_by=sort_column
                # Inclure relations si nécessaire (ex: variant, order_item)
                # include_relations=["variant", "order_item"]
            )
            return PaginatedStockMovementResponse(items=movements, total=total_count)
        except Exception as e:
            logger.error(f"[StockMovementService] Error listing movements: {e}", exc_info=True)
            raise InvalidStockMovementOperationException(f"Erreur interne lors de la récupération des mouvements: {e}")

    async def get_movement(self, movement_id: int) -> StockMovementRead:
        """Récupère un mouvement de stock par ID."""
        logger.debug(f"[StockMovementService] Get Movement ID: {movement_id}")
        movement = await self.movement_crud.get(id=movement_id, schema_to_select=StockMovementRead)
        if not movement:
            raise StockMovementNotFoundException(movement_id)
        return movement

    # La création est souvent une conséquence d'une autre action (commande, restock)
    # Mais une méthode de création directe peut être utile pour des ajustements manuels
    async def create_movement(
        self,
        movement_data: StockMovementCreate,
        # Injecter les CRUD nécessaires à la validation ici
        # variant_crud: VariantCRUDDep,
        # order_item_crud: OrderItemCRUDDep
    ) -> StockMovementRead:
        """Crée un nouveau mouvement de stock (souvent appelé par d'autres services)."""
        logger.info(f"[StockMovementService] Create Movement: VariantID={movement_data.product_variant_id}, Type={movement_data.movement_type}, Change={movement_data.quantity_change}")

        # --- Validation (Optionnelle ici, dépend si c'est un endpoint direct ou interne) ---
        # 1. Vérifier si la variation existe
        # variant_exists = await variant_crud.exists(id=movement_data.product_variant_id)
        # if not variant_exists:
        #     raise VariantNotFoundException(movement_data.product_variant_id)

        # 2. Vérifier si l'order_item existe (si fourni)
        # if movement_data.order_item_id:
        #     order_item_exists = await order_item_crud.exists(id=movement_data.order_item_id)
        #     if not order_item_exists:
        #         raise OrderItemNotFoundException(movement_data.order_item_id)
        # ----------------------------------------------------------------------------------

        try:
            # Note: Cette création de mouvement N'IMPACTE PAS le stock actuel dans la table `stock`.
            # L'impact sur `stock.quantity` doit être géré par le service appelant (ex: StockService).
            created_movement = await self.movement_crud.create(schema=movement_data, schema_to_select=StockMovementRead)
            logger.info(f"[StockMovementService] Movement ID {created_movement.id} created.")
            return created_movement
        except Exception as e:
            logger.error(f"[StockMovementService] Error creating movement for VariantID {movement_data.product_variant_id}: {e}", exc_info=True)
            raise StockMovementCreationFailedException(f"Erreur interne lors de la création du mouvement: {e}")

    # La mise à jour ou suppression des mouvements de stock est généralement déconseillée
    # car ils représentent un historique immuable. Si nécessaire, implémenter avec prudence. 