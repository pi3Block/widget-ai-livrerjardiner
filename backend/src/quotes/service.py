import logging
from typing import Optional
from decimal import Decimal

from src.quotes.models import QuoteCreate, QuoteUpdate, QuoteRead, PaginatedQuoteRead, QuoteItemRead, Quote
from src.quotes.exceptions import (
    QuoteNotFoundException,
    InvalidQuoteStatusException,
    QuoteUpdateForbiddenException,
    QuoteCreationFailedException,
    DuplicateQuoteException,
    QuoteDeletionException,
    QuoteUpdateException
)
from src.products.exceptions import VariantNotFoundException, InvalidOperationException

# Import Repository Interface
from src.quotes.interfaces.repositories import AbstractQuoteRepository

# Import des dépendances pour les autres services/repositories
from src.llm.interfaces import AbstractProductVariantRepository

logger = logging.getLogger(__name__)

# Statuts autorisés pour un devis (exemple)
ALLOWED_QUOTE_STATUS = ["pending", "accepted", "rejected", "expired"]

class QuoteService:
    """Service applicatif pour la gestion des devis, utilisant le pattern Repository."""

    def __init__(self, 
                 quote_repo: AbstractQuoteRepository, 
                 variant_repo: AbstractProductVariantRepository):
        """Initialise le service avec les repositories requis."""
        # Remove self.db = db
        self.quote_repo = quote_repo
        self.variant_repo = variant_repo

    # --- Helper for mapping and total price calculation ---
    def _map_quote_to_read(self, quote_db: Quote) -> QuoteRead:
        """Mappe un objet Quote de la DB vers QuoteRead et calcule le prix total."""
        if not quote_db:
            # This case should ideally not happen if called after a successful fetch
            raise ValueError("Cannot map a None quote object.")
            
        total_price = Decimal(0)
        items_read = []
        if quote_db.items: # Ensure items are loaded
            for item in quote_db.items:
                total_price += item.quantity * item.unit_price
                items_read.append(QuoteItemRead.model_validate(item))
        
        # Create QuoteRead instance
        quote_read = QuoteRead.model_validate(quote_db)
        quote_read.items = items_read
        quote_read.total_price = total_price
        return quote_read

    # --- Service Methods Refactored --- 

    async def get_quote(self, quote_id: int, user_id: Optional[int] = None, is_admin: bool = False) -> QuoteRead:
        """Récupère un devis par ID en utilisant le repository, vérifiant l'accès."""
        logger.debug(f"[QuoteService] Récupération devis ID: {quote_id} via repo pour user: {user_id} (admin: {is_admin})")
        
        # Use repository to get the quote with items
        quote_db = await self.quote_repo.get_by_id_with_items(quote_id=quote_id)
        
        if not quote_db:
            logger.warning(f"[QuoteService] Devis ID {quote_id} non trouvé par le repo.")
            raise QuoteNotFoundException(quote_id)
        
        # Access control check remains the same
        if not is_admin and user_id is not None and quote_db.user_id != user_id:
            logger.warning(f"[QuoteService] Accès refusé devis {quote_id} pour user {user_id}.")
            raise QuoteUpdateForbiddenException(f"Accès non autorisé au devis ID {quote_id}.")
            
        # Map to Read schema with total price calculation
        return self._map_quote_to_read(quote_db)

    async def list_user_quotes(self, user_id: int, limit: int, offset: int) -> PaginatedQuoteRead:
        """Liste les devis pour un utilisateur via le repository."""
        logger.debug(f"[QuoteService] Listage devis pour user ID: {user_id}, limit: {limit}, offset: {offset} via repo")
        
        # Use repository to list quotes
        quotes_db, total_count = await self.quote_repo.list_by_user_id(user_id=user_id, limit=limit, offset=offset)
        
        # Map results to Read schema
        quote_responses = [self._map_quote_to_read(q) for q in quotes_db]

        return PaginatedQuoteRead(items=quote_responses, total=total_count)

    async def create_quote(self, quote_data: QuoteCreate) -> QuoteRead:
        """Crée un nouveau devis via le repository après validation des items."""
        requesting_user_id = quote_data.user_id
        logger.info(f"[QuoteService] Tentative création devis pour user ID: {requesting_user_id} via repo")
                     
        if not quote_data.items:
             raise InvalidOperationException("Impossible de créer un devis sans articles.")

        # Validate each item and ensure correct price from variant repo
        for item_in in quote_data.items:
            variant = await self.variant_repo.get_by_id(item_in.product_variant_id)
            if not variant:
                 logger.error(f"[QuoteService] Variante produit ID {item_in.product_variant_id} non trouvée lors création devis.")
                 raise VariantNotFoundException(variant_id=item_in.product_variant_id)
                 
            current_price = variant.price 
            # Override the price in the input data with the validated price
            if item_in.unit_price != current_price:
                 logger.warning(f"[QuoteService] Prix unitaire fourni ({item_in.unit_price}) différent du prix variante ({current_price}) pour variant {item_in.product_variant_id}. Utilisation du prix de la variante.")
                 item_in.unit_price = current_price

        try:
            # Use repository to create the quote and its items
            # The repository's create_with_items should handle the transaction
            created_quote_db = await self.quote_repo.create_with_items(quote_data=quote_data)
            
            if not created_quote_db:
                 # Should not happen if repo raises exceptions properly
                 logger.error(f"[QuoteService] Repo a retourné None après tentative de création pour user {requesting_user_id}")
                 raise QuoteCreationFailedException("Le repository n'a pas retourné de devis après création.")

            logger.info(f"[QuoteService] Devis ID {created_quote_db.id} créé via repo pour user {requesting_user_id}.")
            
            # Map to Read schema with total price calculation
            # The repo should return the object with items loaded
            return self._map_quote_to_read(created_quote_db)
            
        except (DuplicateQuoteException, QuoteCreationFailedException) as e:
            logger.error(f"[QuoteService] Erreur repo lors création devis pour user {requesting_user_id}: {e}", exc_info=True)
            raise e # Re-raise specific repo exceptions
        except VariantNotFoundException as e:
             logger.error(f"[QuoteService] Erreur variante non trouvée lors création devis: {e}", exc_info=True)
             raise e
        except Exception as e:
            # Catch unexpected errors during the process
            logger.error(f"[QuoteService] Erreur inattendue création devis pour user {requesting_user_id}: {e}", exc_info=True)
            # Wrap in a standard creation exception if it's not already one
            if not isinstance(e, (QuoteCreationFailedException, InvalidOperationException)):
                raise QuoteCreationFailedException(f"Erreur inattendue: {e}")
            else:
                raise e

    async def update_quote_status(self, quote_id: int, status_update_data: QuoteUpdate, requesting_user_id: int, is_admin: bool) -> QuoteRead:
        """Met à jour le statut d'un devis via le repository, vérifiant les droits."""
        new_status = status_update_data.status
        logger.info(f"[QuoteService] Tentative MAJ statut devis ID: {quote_id} à '{new_status}' par user {requesting_user_id} (admin: {is_admin}) via repo")
        
        if new_status not in ALLOWED_QUOTE_STATUS:
            logger.warning(f"[QuoteService] Tentative MAJ devis {quote_id} avec statut invalide: {new_status}")
            raise InvalidQuoteStatusException(status=new_status, allowed=ALLOWED_QUOTE_STATUS)
        
        # 1. Get current quote using repo to check ownership/existence
        quote_db = await self.quote_repo.get_by_id_with_items(quote_id=quote_id)
        if not quote_db:
            raise QuoteNotFoundException(quote_id)
        
        # 2. Check permissions
        if not is_admin and quote_db.user_id != requesting_user_id:
            logger.warning(f"[QuoteService] Accès refusé MAJ statut devis {quote_id} par user {requesting_user_id}.")
            raise QuoteUpdateForbiddenException(f"Accès non autorisé à modifier le statut du devis ID {quote_id}.")
                    
        # 3. Call repository to update status
        try:
            # Pass the QuoteUpdate schema directly to the repository
            updated_quote_db = await self.quote_repo.update_status(
                quote_id=quote_id, 
                status_update=status_update_data
            )
            
            if not updated_quote_db:
                 # Should be handled by repo raising QuoteNotFoundException or similar, but as a safeguard:
                 logger.error(f"[QuoteService] Repo a retourné None après MAJ statut pour devis {quote_id}, attendu une exception.")
                 raise QuoteUpdateException(quote_id=quote_id, detail="Le repository n'a pas retourné le devis mis à jour.")
                 
            logger.info(f"[QuoteService] Statut devis ID {quote_id} mis à jour à '{new_status}' via repo.")
            # Map to Read schema with total price calculation
            return self._map_quote_to_read(updated_quote_db)
            
        except (QuoteNotFoundException, QuoteUpdateException) as e:
             logger.error(f"[QuoteService] Erreur repo lors MAJ statut devis {quote_id}: {e}", exc_info=True)
             raise e # Re-raise specific repo exceptions
        except Exception as e:
             logger.error(f"[QuoteService] Erreur inattendue MAJ statut devis {quote_id}: {e}", exc_info=True)
             if not isinstance(e, InvalidQuoteStatusException):
                 raise QuoteUpdateException(quote_id=quote_id, detail=f"Erreur inattendue: {e}")
             else:
                 raise e
                 
    # --- Add delete method if needed ---
    async def delete_quote(self, quote_id: int, requesting_user_id: int, is_admin: bool) -> bool:
        """Supprime un devis via le repository, vérifiant les droits."""
        logger.info(f"[QuoteService] Tentative suppression devis ID: {quote_id} par user {requesting_user_id} (admin: {is_admin}) via repo")

        # 1. Get current quote using repo to check ownership/existence
        quote_db = await self.quote_repo.get_by_id_with_items(quote_id=quote_id)
        if not quote_db:
            # Decide whether to raise or return False based on API contract
            logger.warning(f"[QuoteService] Tentative suppression devis ID {quote_id} non trouvé.")
            return False # Or raise QuoteNotFoundException(quote_id)
        
        # 2. Check permissions
        if not is_admin and quote_db.user_id != requesting_user_id:
            logger.warning(f"[QuoteService] Accès refusé suppression devis {quote_id} par user {requesting_user_id}.")
            raise QuoteUpdateForbiddenException(f"Accès non autorisé à supprimer le devis ID {quote_id}.")

        # 3. Call repository to delete
        try:
            deleted = await self.quote_repo.delete_quote(quote_id=quote_id)
            if deleted:
                logger.info(f"[QuoteService] Devis ID {quote_id} supprimé avec succès via repo.")
            else:
                # This might indicate the quote was deleted between the check and the delete call, 
                # or the repo method returns False if not found.
                logger.warning(f"[QuoteService] Repo a indiqué échec suppression devis {quote_id}. Il n'existait peut-être déjà plus.")
            return deleted
        except QuoteDeletionException as e:
            logger.error(f"[QuoteService] Erreur repo lors suppression devis {quote_id}: {e}", exc_info=True)
            raise e
        except Exception as e:
            logger.error(f"[QuoteService] Erreur inattendue suppression devis {quote_id}: {e}", exc_info=True)
            raise QuoteDeletionException(quote_id=quote_id, detail=f"Erreur inattendue: {e}")


# Remove old internal methods (_get_by_id, _list_and_count_for_user, _add, _update_status)

# Remove old internal methods (_get_by_id, _list_and_count_for_user, _add, _update_status) 