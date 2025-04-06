import logging
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy import select, func, update as sqlalchemy_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Modèles SQLAlchemy (depuis nouvel emplacement)
from src.database import models

# Entités Domaine
from ..domain.entities import Quote, QuoteItem

# Exceptions Domaine - Correction import
from ..domain.exceptions import QuoteNotFoundException

# Domaine Quotes
from src.quotes.domain.repositories import AbstractQuoteRepository

logger = logging.getLogger(__name__)

class SQLAlchemyQuoteRepository(AbstractQuoteRepository):
    """Implémentation SQLAlchemy du repository de Devis."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, quote_id: int) -> Optional[Quote]:
        """Récupère un devis par son ID, incluant ses items."""
        stmt = select(models.QuoteDB).where(models.QuoteDB.id == quote_id)
        # Charger les items et potentiellement les variantes associées aux items
        stmt = stmt.options(
            selectinload(models.QuoteDB.items).selectinload(models.QuoteItemDB.product_variant) 
            # Charger l'utilisateur si nécessaire:
            # selectinload(models.QuoteDB.user)
        )
        result = await self.session.execute(stmt)
        quote_db = result.scalar_one_or_none()
        
        if not quote_db:
            logger.debug(f"Devis ID {quote_id} non trouvé dans get_by_id().")
            return None
        
        # Mapper vers l'entité Pydantic du domaine
        return Quote.model_validate(quote_db)

    async def list_for_user(self, user_id: int, limit: int, offset: int) -> List[Quote]:
        """Liste les devis pour un utilisateur donné avec pagination."""
        stmt = (
            select(models.QuoteDB)
            .where(models.QuoteDB.user_id == user_id)
            .options(selectinload(models.QuoteDB.items)) # Charger les items
            .order_by(models.QuoteDB.created_at.desc()) # Trier par date récente
            .limit(limit)
            .offset(offset)
        )
               
        result = await self.session.execute(stmt)
        quotes_db = result.scalars().all()
        return [Quote.model_validate(q_db) for q_db in quotes_db]

    async def add(self, quote_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Quote:
        """Ajoute un nouveau devis avec ses items."""
        # Créer l'objet QuoteDB principal
        new_quote_db = models.QuoteDB(**quote_data)
        self.session.add(new_quote_db)
        
        # Créer les objets QuoteItemDB et les lier
        # Pas besoin de les ajouter explicitement à la session si la relation cascade est bien configurée
        new_quote_db.items = [models.QuoteItemDB(**item) for item in items_data]
        
        try:
            # flush pour obtenir l'ID du devis et vérifier les contraintes initiales
            await self.session.flush()
            # refresh pour charger les relations (items notamment)
            await self.session.refresh(new_quote_db, attribute_names=['items'])
            logger.info(f"Devis ID {new_quote_db.id} ajouté pour user {new_quote_db.user_id}.")
            # Mapper vers l'entité Pydantic avant de retourner
            return Quote.model_validate(new_quote_db)
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erreur intégrité ajout devis pour user {quote_data.get('user_id')}: {e}", exc_info=True)
            # Vérifier si l'erreur est due à une clé étrangère (user_id, variant_id)
            # ou une autre contrainte
            raise QuoteNotFoundException(f"Violation contrainte ajout devis: {e.orig}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue ajout devis pour user {quote_data.get('user_id')}: {e}", exc_info=True)
            raise

    async def update_status(self, quote_id: int, status: str) -> Optional[Quote]:
        """Met à jour le statut d'un devis."""
        # Utiliser session.get pour récupérer le devis par PK
        quote_db = await self.session.get(models.QuoteDB, quote_id)
        if not quote_db:
            logger.warning(f"Tentative MAJ statut devis ID {quote_id} non trouvé.")
            return None # Ou lever QuoteNotFoundException selon le contrat

        if quote_db.status == status:
             logger.info(f"Statut devis {quote_id} déjà '{status}'. Aucune MAJ nécessaire.")
             # Recharger les items avant de retourner l'objet validé
             await self.session.refresh(quote_db, attribute_names=['items'])
             return Quote.model_validate(quote_db) 

        # Mettre à jour le statut et la date de mise à jour
        quote_db.status = status
        # quote_db.updated_at = datetime.utcnow() # SQLAlchemy le gère peut-être déjà
        
        try:
            await self.session.flush() # Appliquer le changement
            await self.session.refresh(quote_db, attribute_names=['items']) # Recharger avec les items
            logger.info(f"Statut devis ID {quote_id} mis à jour à '{status}'.")
            return Quote.model_validate(quote_db)
        except Exception as e:
             await self.session.rollback()
             logger.error(f"Erreur inattendue MAJ statut devis {quote_id}: {e}", exc_info=True)
             raise 