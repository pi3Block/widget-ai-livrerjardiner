import logging
from typing import Optional, List, TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel
import asyncio

# Import des fonctions CRUD de stock
from . import crud as stock_crud

# Import des modèles et schémas (si nécessaire pour le typage de retour/entrée)
from .models import StockRead, StockUpdate # Assurez-vous que StockRead/StockUpdate existent si besoin

# Import génériques pour pagination
from typing import TypeVar, Generic
from sqlmodel import SQLModel

# Import des exceptions
from src.products.exceptions import StockNotFoundException, InsufficientStockException

logger = logging.getLogger(__name__)

# --- Schéma de Pagination pour Stock ---
# Déplacé ici car spécifique au service/API et non un modèle DB
class PaginatedStockResponse(SQLModel, Generic[StockRead]):
    items: List[StockRead]
    total: int
# --- Fin Schéma Pagination ---

class StockService:
    """Service applicatif pour la gestion des stocks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        logger.info("StockService initialisé.")

    async def get_stock_for_variant(self, product_variant_id: int) -> Optional[StockRead]:
        """Récupère les informations de stock pour une variante.
           Retourne un schéma StockRead ou None si non trouvé.
        """
        logger.debug(f"[StockService] Récupération stock pour variant ID: {product_variant_id}")
        stock_orm = await stock_crud.get_stock_for_variant(self.db, product_variant_id)
        if not stock_orm:
            return None
        return StockRead.model_validate(stock_orm)

    async def update_stock_quantity(
        self, 
        product_variant_id: int, 
        quantity_change: int
    ) -> StockRead:
        """Met à jour la quantité de stock pour une variante.
           quantity_change peut être positif (ajout) ou négatif (retrait).
           Lève StockNotFoundException ou InsufficientStockException.
           Retourne le schéma StockRead mis à jour.
        """
        logger.info(f"[StockService] Mise à jour stock pour variant ID: {product_variant_id}, changement: {quantity_change}")
        try:
            updated_stock_orm = await stock_crud.update_stock_quantity(
                self.db, 
                product_variant_id,
                quantity_change
            )
            return StockRead.model_validate(updated_stock_orm)
        except (StockNotFoundException, InsufficientStockException) as e:
            logger.error(f"[StockService] Erreur MAJ stock pour variant {product_variant_id}: {e}")
            raise e
        except Exception as e:
            logger.exception(f"[StockService] Erreur inattendue MAJ stock pour variant {product_variant_id}: {e}")
            raise Exception(f"Erreur interne lors de la mise à jour du stock: {e}")

    async def get_stocks_for_variants(self, variant_ids: List[int]) -> List[StockRead]:
        """Récupère les informations de stock pour une liste de variantes."""
        if not variant_ids:
            return []
        logger.debug(f"[StockService] Récupération stock pour variantes IDs: {variant_ids}")
        try:
            stock_orms = await stock_crud.get_stocks_for_variants(self.db, variant_ids)
            return [StockRead.model_validate(s) for s in stock_orms]
        except Exception as e:
            logger.error(f"[StockService] Erreur CRUD lors de get_stocks_for_variants: {e}", exc_info=True)
            raise Exception(f"Erreur interne récupération multiple stocks: {e}")

    async def update_stock_details(
        self, 
        product_variant_id: int, 
        stock_update: StockUpdate
    ) -> StockRead:
        """Met à jour les détails du stock (quantité et/ou seuil) pour une variante."""
        logger.info(f"[StockService] Mise à jour détails stock pour variant ID: {product_variant_id} avec données: {stock_update.model_dump(exclude_unset=True)}")
        
        update_data = stock_update.model_dump(exclude_unset=True)
        if not update_data:
             raise ValueError("Aucune donnée fournie pour la mise à jour.")
             
        # La validation de quantité < 0 est maintenant gérée dans CRUD
        
        try:
            updated_stock_orm = await stock_crud.update_stock_details(self.db, product_variant_id, update_data)
            return StockRead.model_validate(updated_stock_orm)
        except StockNotFoundException as e:
            logger.warning(f"[StockService] Stock non trouvé pour MAJ détails, variant ID: {product_variant_id}: {e}")
            raise e # Re-lever l'exception métier spécifique
        except ValueError as ve:
             logger.warning(f"[StockService] Données invalides pour MAJ détails stock variante {product_variant_id}: {ve}")
             raise ve # Re-lever l'exception de validation
        except Exception as e:
            logger.error(f"[StockService] Erreur CRUD/inattendue lors de update_stock_details: {e}", exc_info=True)
            raise Exception(f"Erreur interne mise à jour détails stock: {e}")

    async def list_low_stock_variants(
        self, 
        threshold: int, 
        limit: int = 50, 
        offset: int = 0
    ) -> PaginatedStockResponse:
        """Liste les entrées de stock dont la quantité est inférieure ou égale au seuil."""
        logger.debug(f"[StockService] Listage stock bas (<= {threshold}), limit={limit}, offset={offset}")
        try:
            low_stock_orms, total_count = await stock_crud.list_low_stock(self.db, threshold, limit, offset)
            items_read = [StockRead.model_validate(s) for s in low_stock_orms]
            return PaginatedStockResponse(items=items_read, total=total_count)
        except Exception as e:
            logger.error(f"[StockService] Erreur CRUD lors de list_low_stock: {e}", exc_info=True)
            raise Exception(f"Erreur interne listage stock bas: {e}")

    # TODO: Ajouter d'autres méthodes si nécessaire, par exemple:
    # async def list_low_stock_variants(self, threshold: int) -> List[StockRead]:
    #     """Liste les variantes dont le stock est inférieur ou égal au seuil."""
    #     # Implémenter la logique ici, potentiellement avec une fonction CRUD dédiée
    #     pass

    # async def set_initial_stock(self, product_variant_id: int, quantity: int, alert_threshold: Optional[int] = None) -> StockRead:
    #     """Définit le stock initial pour une nouvelle variante."""
    #     # Vérifier si le stock existe déjà? Créer ou mettre à jour?
    #     # Utiliser une fonction CRUD dédiée
    #     pass 