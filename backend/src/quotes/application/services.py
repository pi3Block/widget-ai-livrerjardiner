import logging
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal

# Repositories (Interfaces)
from src.quotes.domain.repositories import AbstractQuoteRepository
from src.products.domain.repositories import AbstractProductVariantRepository # Pour valider/prix

# Entités du Domaine
from src.quotes.domain.entities import Quote

# Schémas/DTOs de l'Application
from .schemas import QuoteCreate, QuoteUpdate, QuoteResponse, QuoteItemCreate

# Exceptions du Domaine
from src.quotes.domain.exceptions import QuoteNotFoundException, InvalidQuoteStatusException, QuoteUpdateForbiddenException
from src.products.domain.exceptions import VariantNotFoundException # Pour gérer produit non trouvé
from src.products.domain.exceptions import InvalidOperationException # Si autre erreur validation

logger = logging.getLogger(__name__)

# Statuts autorisés pour un devis (exemple)
ALLOWED_QUOTE_STATUS = ["pending", "accepted", "rejected", "expired"]

class QuoteService:
    """Service applicatif pour la gestion des devis."""

    def __init__(self, 
                 quote_repo: AbstractQuoteRepository, 
                 variant_repo: AbstractProductVariantRepository):
        self.quote_repo = quote_repo
        self.variant_repo = variant_repo

    async def get_quote(self, quote_id: int, user_id: Optional[int] = None, is_admin: bool = False) -> Optional[QuoteResponse]:
        """Récupère un devis par ID, vérifiant l'accès utilisateur si nécessaire."""
        logger.debug(f"[QuoteService] Récupération devis ID: {quote_id} pour user: {user_id} (admin: {is_admin})")
        quote_entity = await self.quote_repo.get_by_id(quote_id)
        if not quote_entity:
            logger.warning(f"[QuoteService] Devis ID {quote_id} non trouvé.")
            return None
        
        # Vérification des droits d'accès
        if not is_admin and user_id is not None and quote_entity.user_id != user_id:
            logger.warning(f"[QuoteService] Accès refusé devis {quote_id} pour user {user_id}.")
            raise QuoteUpdateForbiddenException(f"Accès non autorisé au devis ID {quote_id}.") # Ou une exception PermissionDenied
            
        return QuoteResponse.model_validate(quote_entity)

    async def list_user_quotes(self, user_id: int, limit: int, offset: int) -> Tuple[List[QuoteResponse], int]:
        """Liste les devis pour un utilisateur spécifique et retourne le compte total."""
        logger.debug(f"[QuoteService] Listage devis pour user ID: {user_id}, limit: {limit}, offset: {offset}")
        # Le repo gère déjà le filtrage par user_id
        quote_entities = await self.quote_repo.list_for_user(user_id, limit, offset)
        
        # Obtenir le compte total via une méthode dédiée du repository
        total_count = await self.quote_repo.count_for_user(user_id)
        
        quote_responses = [QuoteResponse.model_validate(q) for q in quote_entities]
        return quote_responses, total_count

    async def create_quote(self, quote_data: QuoteCreate, requesting_user_id: int) -> QuoteResponse:
        """Crée un nouveau devis après validation des items."""
        logger.info(f"[QuoteService] Tentative création devis pour user ID: {requesting_user_id}")
        if quote_data.user_id != requesting_user_id:
             logger.warning(f"[QuoteService] Incohérence user ID création devis (demandeur: {requesting_user_id}, payload: {quote_data.user_id}). Utilisation ID demandeur.")
             quote_data.user_id = requesting_user_id
             
        if not quote_data.items:
             raise InvalidOperationException("Impossible de créer un devis sans articles.")

        validated_items_data = []
        calculated_total = Decimal(0)
        
        # Valider chaque item et récupérer le prix depuis la variante
        for item_in in quote_data.items:
            variant = await self.variant_repo.get(item_in.product_variant_id)
            if not variant:
                 logger.error(f"[QuoteService] Variante produit ID {item_in.product_variant_id} non trouvée lors création devis.")
                 raise VariantNotFoundException(variant_id=item_in.product_variant_id)
                 
            # Utiliser le prix de la variante trouvée
            current_price = variant.price 
            item_total = current_price * item_in.quantity
            calculated_total += item_total
            
            validated_items_data.append({
                "product_variant_id": item_in.product_variant_id,
                "quantity": item_in.quantity,
                "unit_price": current_price # Prix validé
            })

        # Préparer les données principales du devis
        quote_main_data = {
            "user_id": quote_data.user_id,
            "status": quote_data.status or "pending", # Assurer un statut par défaut
            "total_price": calculated_total # Stocker le total calculé
        }

        try:
            created_quote_entity = await self.quote_repo.add(
                quote_data=quote_main_data, 
                items_data=validated_items_data
            )
            logger.info(f"[QuoteService] Devis ID {created_quote_entity.id} créé pour user {quote_data.user_id}.")
            # Recharger pour être sûr d'avoir toutes les données (items inclus)
            full_quote = await self.quote_repo.get_by_id(created_quote_entity.id)
            if not full_quote:
                logger.error(f"[QuoteService] Erreur rechargement devis {created_quote_entity.id} après création!")
                raise InvalidOperationException("Erreur interne après création devis.")
            return QuoteResponse.model_validate(full_quote)
        except InvalidOperationException as e:
            logger.error(f"[QuoteService] Erreur repo création devis: {e}")
            raise e
        except Exception as e:
            logger.error(f"[QuoteService] Erreur inattendue création devis: {e}", exc_info=True)
            raise

    async def update_quote_status(self, quote_id: int, status_update: str, requesting_user_id: int, is_admin: bool) -> QuoteResponse:
        """Met à jour le statut d'un devis, vérifiant les droits."""
        logger.info(f"[QuoteService] Tentative MAJ statut devis ID: {quote_id} à '{status_update}' par user {requesting_user_id} (admin: {is_admin})")
        
        if status_update not in ALLOWED_QUOTE_STATUS:
            logger.warning(f"[QuoteService] Tentative MAJ devis {quote_id} avec statut invalide: {status_update}")
            raise InvalidQuoteStatusException(status=status_update, allowed=ALLOWED_QUOTE_STATUS)
        
        # Récupérer le devis existant
        quote_entity = await self.quote_repo.get_by_id(quote_id)
        if not quote_entity:
            raise QuoteNotFoundException(quote_id)
        
        # Vérifier les droits
        if not is_admin and quote_entity.user_id != requesting_user_id:
            logger.warning(f"[QuoteService] Accès refusé MAJ statut devis {quote_id} par user {requesting_user_id}.")
            raise QuoteUpdateForbiddenException(f"Accès non autorisé à modifier le statut du devis ID {quote_id}.")
            
        # Vérifier si la transition de statut est autorisée (logique métier potentielle)
        # Ex: Un devis 'accepted' ne peut pas revenir à 'pending'?
        # if quote_entity.status == 'accepted' and status_update == 'pending':
        #     raise InvalidOperationException("Impossible de changer un devis accepté en pending.")
            
        try:
            updated_quote_entity = await self.quote_repo.update_status(quote_id, status_update)
            if not updated_quote_entity:
                 # Devrait être impossible si get_by_id a réussi, mais sécurité
                 raise QuoteNotFoundException(quote_id)
                 
            logger.info(f"[QuoteService] Statut devis ID {quote_id} mis à jour à '{status_update}'.")
            return QuoteResponse.model_validate(updated_quote_entity)
        except Exception as e:
             logger.error(f"[QuoteService] Erreur inattendue MAJ statut devis {quote_id}: {e}", exc_info=True)
             raise 