import logging
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
import asyncio # Pour gérer potentiellement plusieurs opérations atomiques

# Repositories (Interfaces)
from src.orders.domain.repositories import AbstractOrderRepository
from src.products.domain.repositories import AbstractProductVariantRepository, AbstractStockRepository
from src.addresses.domain.repositories import AbstractAddressRepository # Pour valider adresses

# Entités du Domaine
from src.orders.domain.entities import Order

# Schémas/DTOs de l'Application
from .schemas import OrderCreate, OrderUpdate, OrderResponse, OrderItemCreate

# Exceptions du Domaine
from src.orders.domain.exceptions import (
    OrderNotFoundException, InvalidOrderStatusException, 
    OrderUpdateForbiddenException, OrderCreationFailedException
)
from src.products.domain.exceptions import (
    VariantNotFoundException, InsufficientStockException, StockNotFoundException
)
from ...addresses.domain.exceptions import AddressNotFoundException
from src.products.domain.exceptions import InvalidOperationException # Autres erreurs

# --- Service Email --- 
from src.email.application.services import EmailService # Importer le service email

logger = logging.getLogger(__name__)

# Statuts autorisés pour une commande (exemple)
ALLOWED_ORDER_STATUS = ["pending", "processing", "shipped", "delivered", "cancelled"]

class OrderService:
    """Service applicatif pour la gestion des commandes."""

    def __init__(self, 
                 order_repo: AbstractOrderRepository, 
                 variant_repo: AbstractProductVariantRepository,
                 stock_repo: AbstractStockRepository,
                 address_repo: AbstractAddressRepository,
                 email_service: EmailService): # Injecter EmailService
        self.order_repo = order_repo
        self.variant_repo = variant_repo
        self.stock_repo = stock_repo
        self.address_repo = address_repo
        self.email_service = email_service # Stocker l'instance

    async def get_order(self, order_id: int, user_id: Optional[int] = None, is_admin: bool = False) -> Optional[OrderResponse]:
        """Récupère une commande par ID, vérifiant l'accès utilisateur si nécessaire."""
        logger.debug(f"[OrderService] Récupération commande ID: {order_id} pour user: {user_id} (admin: {is_admin})")
        order_entity = await self.order_repo.get_by_id(order_id)
        if not order_entity:
            logger.warning(f"[OrderService] Commande ID {order_id} non trouvée.")
            return None
        
        # Vérification des droits d'accès
        if not is_admin and user_id is not None and order_entity.user_id != user_id:
            logger.warning(f"[OrderService] Accès refusé commande {order_id} pour user {user_id}.")
            raise OrderUpdateForbiddenException(f"Accès non autorisé à la commande ID {order_id}.")
            
        return OrderResponse.model_validate(order_entity)

    async def list_user_orders(self, user_id: int, limit: int, offset: int) -> Tuple[List[OrderResponse], int]:
        """Liste les commandes pour un utilisateur spécifique."""
        logger.debug(f"[OrderService] Listage commandes pour user ID: {user_id}, limit: {limit}, offset: {offset}")
        order_entities = await self.order_repo.list_for_user(user_id, limit, offset)
        # !! TODO: Améliorer le comptage pour la pagination (via repo) !!
        total_count = len(order_entities)
        logger.warning("[OrderService] Le comptage total des commandes pour la pagination est approximatif.")
        
        order_responses = [OrderResponse.model_validate(o) for o in order_entities]
        return order_responses, total_count

    async def create_order(self, order_data: OrderCreate, requesting_user_id: int) -> OrderResponse:
        """Crée une nouvelle commande, valide les items/stock/adresses, décrémente le stock et envoie email."""
        logger.info(f"[OrderService] Tentative création commande pour user ID: {requesting_user_id}")
        if order_data.user_id != requesting_user_id:
             logger.warning(f"[OrderService] Incohérence user ID création commande (demandeur: {requesting_user_id}, payload: {order_data.user_id}). Utilisation ID demandeur.")
             order_data.user_id = requesting_user_id
             
        if not order_data.items:
             raise InvalidOperationException("Impossible de créer une commande sans articles.")

        # 1. Valider les adresses
        try:
            delivery_address_db = await self.address_repo.get_address_by_id(order_data.delivery_address_id)
            billing_address_db = await self.address_repo.get_address_by_id(order_data.billing_address_id)
            if not delivery_address_db or not billing_address_db:
                 raise AddressNotFoundException(address_id=0) # ID non pertinent ici
            # Vérifier que les adresses appartiennent bien à l'utilisateur
            if delivery_address_db.user_id != requesting_user_id or billing_address_db.user_id != requesting_user_id:
                 raise OrderUpdateForbiddenException("Les adresses fournies n'appartiennent pas à l'utilisateur.")
        except AddressNotFoundException:
            logger.error(f"[OrderService] Adresse ID {order_data.delivery_address_id} ou {order_data.billing_address_id} non trouvée pour user {requesting_user_id}.")
            raise OrderCreationFailedException("Adresse de livraison ou de facturation invalide.")
        except OrderUpdateForbiddenException as e:
            logger.error(f"[OrderService] Tentative d'utilisation d'adresse non autorisée pour user {requesting_user_id}.")
            raise e
            
        validated_items_data = []
        calculated_total = Decimal(0)
        stock_decrements: Dict[int, int] = {} # variant_id -> quantity_to_decrement
        item_details_for_email = [] # Pour l'email

        # 2. Valider chaque item, vérifier le stock et préparer les données
        try:
            variant_ids = [item.product_variant_id for item in order_data.items]
            # Charger toutes les variantes et stocks nécessaires en une fois si possible (via repo?)
            # Pour l'instant, boucle simple
            for item_in in order_data.items:
                variant = await self.variant_repo.get(item_in.product_variant_id)
                if not variant:
                    raise VariantNotFoundException(variant_id=item_in.product_variant_id)
                
                # Récupérer le stock actuel
                stock_info = await self.stock_repo.get_for_variant(variant.id)
                current_stock = stock_info.quantity if stock_info else 0
                
                if current_stock < item_in.quantity:
                    raise InsufficientStockException(variant.id, item_in.quantity, current_stock)
                
                current_price = variant.price 
                item_total = current_price * item_in.quantity
                calculated_total += item_total
                
                validated_items_data.append({
                    "product_variant_id": variant.id,
                    "quantity": item_in.quantity,
                    "unit_price": current_price
                })
                stock_decrements[variant.id] = item_in.quantity
                # Ajouter détails pour email
                item_details_for_email.append({
                     "variant_sku": variant.sku,
                     "quantity": item_in.quantity,
                     "price_at_order": current_price,
                     "variant_details": { "name": variant.name } # Ajouter d'autres infos variant si besoin
                })
                
        except VariantNotFoundException as e:
             logger.error(f"[OrderService] Variante {e.variant_id} non trouvée lors création commande.")
             raise OrderCreationFailedException(f"Produit ID {e.variant_id} non trouvé.")
        except InsufficientStockException as e:
             logger.error(f"[OrderService] Stock insuffisant pour variante {e.variant_id} (demandé: {e.requested}, dispo: {e.available}).")
             raise OrderCreationFailedException(f"Stock insuffisant pour un produit (ID: {e.variant_id}).")
        except StockNotFoundException as e:
            logger.error(f"[OrderService] Stock non trouvé pour variante {e.variant_id} lors création commande.")
            raise OrderCreationFailedException(f"Erreur de stock pour produit ID {e.variant_id}.")

        # 3. Préparer les données de la commande principale
        order_main_data = {
            "user_id": order_data.user_id,
            "status": order_data.status or "pending",
            "total_price": calculated_total,
            "delivery_address_id": order_data.delivery_address_id,
            "billing_address_id": order_data.billing_address_id
        }

        # 4. Créer la commande et décrémenter le stock
        try:
            created_order_entity = await self.order_repo.add(
                order_data=order_main_data, 
                items_data=validated_items_data
            )
            logger.info(f"[OrderService] Commande ID {created_order_entity.id} ajoutée à la DB pour user {order_data.user_id}.")

            # 4b. Décrémenter le stock
            decrement_tasks = [self.stock_repo.update_quantity(var_id, -qty) for var_id, qty in stock_decrements.items()]
            results = await asyncio.gather(*decrement_tasks, return_exceptions=True)
            
            # Vérifier les erreurs potentielles pendant la décrémentation
            failed_decrements = []
            for i, result in enumerate(results):
                 if isinstance(result, Exception):
                      variant_id = list(stock_decrements.keys())[i]
                      logger.error(f"[OrderService] Échec décrémentation stock pour varID {variant_id} (commande {created_order_entity.id}): {result}", exc_info=isinstance(result, Exception))
                      failed_decrements.append(variant_id)
            
            if failed_decrements:
                logger.error(f"[OrderService] Échec décrémentation stock pour commande {created_order_entity.id}. Variantes: {failed_decrements}. La commande a été créée mais le stock est incohérent!")
                raise OrderCreationFailedException("Erreur lors de la mise à jour du stock après création de la commande.")
            
            logger.info(f"[OrderService] Stock décrémenté avec succès pour commande ID {created_order_entity.id}.")
            
            # Recharger la commande complète
            full_order = await self.order_repo.get_by_id(created_order_entity.id)
            if not full_order:
                 logger.error(f"[OrderService] Erreur rechargement commande {created_order_entity.id} après création et décrémentation stock!")
                 raise OrderCreationFailedException("Erreur interne après création commande.")
                 
            # 5. Envoyer l'email de confirmation (après succès transaction)
            try:
                 user_info = full_order.user # Assumer que user est chargé par get_by_id
                 if user_info and user_info.email:
                      logger.info(f"[OrderService] Préparation envoi email confirmation commande {full_order.id} à {user_info.email}")
                      order_details_for_email = {
                          "id": full_order.id,
                          "user_name": user_info.name,
                          "total_amount": full_order.total_price,
                          "items": item_details_for_email, # Utiliser les détails collectés plus tôt
                          "delivery_address": full_order.delivery_address.model_dump() if full_order.delivery_address else None
                      }
                      await self.email_service.send_order_confirmation_email(
                          recipient_email=user_info.email,
                          order_details=order_details_for_email
                      )
                 else:
                      logger.warning(f"[OrderService] Impossible d'envoyer email confirmation pour commande {full_order.id}: email utilisateur manquant.")
                      
            except Exception as email_error:
                 # Ne pas faire échouer la création de commande si l'email échoue
                 logger.error(f"[OrderService] Erreur lors de l'envoi de l'email de confirmation pour commande {full_order.id}: {email_error}", exc_info=True)
            
            return OrderResponse.model_validate(full_order)
            
        except Exception as e:
            logger.error(f"[OrderService] Erreur lors de la transaction de création de commande / décrémentation stock: {e}", exc_info=True)
            if not isinstance(e, OrderCreationFailedException):
                raise OrderCreationFailedException(f"Impossible de finaliser la commande: {e}")
            else:
                raise e

    async def update_order_status(self, order_id: int, status_update: str, requesting_user_id: int, is_admin: bool) -> OrderResponse:
        """Met à jour le statut d'une commande, vérifiant les droits."""
        logger.info(f"[OrderService] Tentative MAJ statut commande ID: {order_id} à '{status_update}' par user {requesting_user_id} (admin: {is_admin})")
        
        if status_update not in ALLOWED_ORDER_STATUS:
            raise InvalidOrderStatusException(status=status_update, allowed=ALLOWED_ORDER_STATUS)
        
        order_entity = await self.order_repo.get_by_id(order_id)
        if not order_entity:
            raise OrderNotFoundException(order_id)
        
        if not is_admin and order_entity.user_id != requesting_user_id:
             raise OrderUpdateForbiddenException(f"Accès non autorisé à modifier le statut de la commande ID {order_id}.")
             
        # Logique métier additionnelle ? (ex: ne pas annuler une commande expédiée ?)
        # if order_entity.status == 'shipped' and status_update == 'cancelled':
        #      raise InvalidOperationException("Impossible d'annuler une commande déjà expédiée.")
        
        # Si le statut est 'cancelled', faut-il remettre le stock ? OUI.
        if status_update == 'cancelled' and order_entity.status != 'cancelled':
            logger.info(f"[OrderService] Annulation commande {order_id}, tentative de réajustement du stock.")
            increment_tasks = []
            for item in order_entity.items:
                 increment_tasks.append(self.stock_repo.update_quantity(item.product_variant_id, item.quantity))
            try:
                 results = await asyncio.gather(*increment_tasks, return_exceptions=True)
                 # Vérifier les erreurs potentielles ici aussi ? Logguer si échec.
                 failed_increments = []
                 for i, result in enumerate(results):
                     if isinstance(result, Exception):
                         variant_id = order_entity.items[i].product_variant_id
                         logger.error(f"[OrderService] Échec réajustement stock pour varID {variant_id} (commande annulée {order_id}): {result}", exc_info=True)
                         failed_increments.append(variant_id)
                 if not failed_increments:
                    logger.info(f"[OrderService] Stock réajusté pour commande annulée {order_id}.")
                 else:
                     logger.error(f"[OrderService] Échec réajustement stock pour certaines variantes commande annulée {order_id}: {failed_increments}")
            except Exception as stock_err:
                 logger.error(f"[OrderService] Erreur lors du réajustement du stock pour commande annulée {order_id}: {stock_err}", exc_info=True)
                 # Continuer quand même la mise à jour du statut ? Ou lever une erreur ?
                 # Pour l'instant, on continue mais on log l'erreur.
        
        try:
            updated_order_entity = await self.order_repo.update_status(order_id, status_update)
            if not updated_order_entity:
                 # Cela ne devrait pas arriver si get_by_id a fonctionné avant, mais sécurité
                 raise OrderNotFoundException(order_id) 
                 
            logger.info(f"[OrderService] Statut commande ID {order_id} mis à jour à '{status_update}'.")
            return OrderResponse.model_validate(updated_order_entity)
        except Exception as e:
             logger.error(f"[OrderService] Erreur inattendue MAJ statut commande {order_id}: {e}", exc_info=True)
             # Si la MAJ status échoue après réajustement stock, on est dans un état incohérent...
             raise InvalidOperationException(f"Erreur lors de la mise à jour finale du statut de la commande {order_id}.") 