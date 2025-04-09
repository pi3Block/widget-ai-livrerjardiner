from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastcrud import FastCRUD
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from src.database import AsyncSessionLocal
from src.quotes.models import Quote, QuoteCreate, QuoteUpdate, QuoteItem, QuoteItemCreate
from src.quotes.interfaces.repositories import AbstractQuoteRepository
from src.quotes.exceptions import QuoteNotFoundException, QuoteCreationFailedException, QuoteUpdateException, QuoteDeletionException, DuplicateQuoteException
from src.products.models import ProductVariant # Assuming ProductVariant exists in products module

class SQLAlchemyQuoteRepository(AbstractQuoteRepository):
    """Implémentation SQLAlchemy du repository des devis."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        # FastCRUD pour les opérations de base sur Quote (sans les items pour l'instant)
        self.crud = FastCRUD[Quote, QuoteCreate, QuoteUpdate](Quote)

    async def get_by_id_with_items(self, *, quote_id: int) -> Optional[Quote]:
        """Récupère un devis par son ID, incluant ses items."""
        statement = (
            select(Quote)
            .where(Quote.id == quote_id)
            .options(selectinload(Quote.items))
        )
        try:
            result = await self.db.execute(statement)
            return result.scalars().one_or_none()
        except SQLAlchemyError as e:
            # Log the error e here using your logger instance
            # logger.error(f"Database error fetching quote {quote_id}: {e}", exc_info=True)
            raise QuoteNotFoundException(quote_id=quote_id) # Removed detail=str(e)

    async def list_by_user_id(self, *, user_id: int, offset: int = 0, limit: int = 100) -> Tuple[List[Quote], int]:
        """Liste les devis pour un utilisateur spécifique avec pagination."""
        try:
            result = await self.crud.get_multi(
                db=self.db,
                offset=offset,
                limit=limit,
                filter={"user_id": user_id},
                sort_columns=["created_at"],
                sort_orders=["desc"],
                # Inclure les items pourrait être coûteux ici, dépend du besoin
                # options=[selectinload(Quote.items)] 
            )
            return result.get('data', []), result.get('total', 0)
        except SQLAlchemyError as e:
            # Log the error e
            # Consider a more specific exception if needed
            raise Exception(f"Error listing quotes for user {user_id}: {e}")

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> Tuple[List[Quote], int]:
        """Liste tous les devis avec pagination."""
        try:
            result = await self.crud.get_multi(
                db=self.db,
                offset=offset,
                limit=limit,
                sort_columns=["created_at"],
                sort_orders=["desc"]
            )
            return result.get('data', []), result.get('total', 0)
        except SQLAlchemyError as e:
            # Log the error e
            raise Exception(f"Error listing all quotes: {e}")

    async def create_with_items(self, *, quote_data: QuoteCreate) -> Quote:
        """Crée un nouveau devis avec ses items dans une transaction."""
        try:
            # 1. Créer l'objet Quote (sans les items pour l'instant)
            # FastCRUD ne gère pas les relations imbriquées directement à la création
            quote_dict = {"user_id": quote_data.user_id, "status": "pending"} # Status initial
            db_quote = Quote(**quote_dict)
            self.db.add(db_quote)
            await self.db.flush() # Pour obtenir l'ID du devis
            await self.db.refresh(db_quote)

            if not db_quote.id:
                 raise QuoteCreationFailedException(detail="Failed to retrieve quote ID after flush.")

            # 2. Créer les QuoteItems associés
            total_price = 0
            for item_data in quote_data.items:
                # Idéalement, valider product_variant_id et récupérer le prix ici
                # Pour simplifier, on utilise le prix fourni dans QuoteItemCreate
                db_item = QuoteItem(
                    **item_data.model_dump(),
                    quote_id=db_quote.id
                )
                self.db.add(db_item)
                # total_price += item_data.quantity * item_data.unit_price # Calculation might happen in service layer

            # 3. Commiter la transaction
            await self.db.commit()
            await self.db.refresh(db_quote) # Rafraîchir pour charger les items créés
            
            # Recharger avec les items explicitement si nécessaire après commit
            # Ceci est important car la relation n'est pas automatiquement chargée après commit/refresh sur l'objet parent seul
            loaded_quote = await self.get_by_id_with_items(quote_id=db_quote.id)
            if not loaded_quote:
                 raise QuoteCreationFailedException(detail="Failed to reload quote with items after commit.")

            return loaded_quote

        except IntegrityError as e:
            await self.db.rollback()
            # Log the error e
            if "unique constraint" in str(e).lower():
                 raise DuplicateQuoteException(detail=f"Integrity error during quote creation: {e}")
            raise QuoteCreationFailedException(detail=f"Database integrity error: {e}")
        except SQLAlchemyError as e:
            await self.db.rollback()
            # Log the error e
            raise QuoteCreationFailedException(detail=f"Database error during quote creation: {e}")
        except Exception as e:
            await self.db.rollback()
            # Log the error e
            raise QuoteCreationFailedException(detail=f"An unexpected error occurred: {e}")


    async def update_status(self, *, quote_id: int, status_update: QuoteUpdate) -> Optional[Quote]:
        """Met à jour le statut d'un devis existant."""
        try:
             # Utiliser FastCRUD.update pour la simplicité de la mise à jour de champ unique
             # Note: FastCRUD.update retourne le modèle mis à jour
             updated_quote = await self.crud.update(
                 db=self.db,
                 object=status_update, # Contient juste le champ 'status'
                 id=quote_id
             )
             if not updated_quote:
                 raise QuoteNotFoundException(quote_id=quote_id)
             
             await self.db.commit()
             await self.db.refresh(updated_quote)
             # Recharger avec les items si nécessaire pour la réponse
             return await self.get_by_id_with_items(quote_id=quote_id)
             
        except SQLAlchemyError as e:
             await self.db.rollback()
             # Log the error e
             raise QuoteUpdateException(quote_id=quote_id, detail=str(e))
        except QuoteNotFoundException: # Re-raise specific exception
             await self.db.rollback()
             raise
        except Exception as e:
             await self.db.rollback()
             # Log the error e
             raise QuoteUpdateException(quote_id=quote_id, detail=f"An unexpected error occurred: {e}")

    async def delete_quote(self, *, quote_id: int) -> bool:
        """Supprime un devis et ses items associés."""
        # Note: La suppression en cascade devrait être configurée au niveau de la DB/SQLAlchemy
        # Si ce n'est pas le cas, il faudrait supprimer les items manuellement d'abord.
        quote_to_delete = await self.get_by_id_with_items(quote_id=quote_id)
        if not quote_to_delete:
            # Consider raising QuoteNotFoundException or returning False based on desired behavior
            return False 
            # raise QuoteNotFoundException(quote_id=quote_id)

        try:
            # Utiliser FastCRUD.delete
            await self.crud.delete(db=self.db, id=quote_id)
            await self.db.commit()
            return True
        except SQLAlchemyError as e:
            await self.db.rollback()
            # Log the error e
            raise QuoteDeletionException(quote_id=quote_id, detail=str(e))
        except Exception as e:
            await self.db.rollback()
            # Log the error e
            raise QuoteDeletionException(quote_id=quote_id, detail=f"An unexpected error occurred: {e}") 