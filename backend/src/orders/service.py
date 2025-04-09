import logging
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
import asyncio # Pour gérer potentiellement plusieurs opérations atomiques
from datetime import datetime # Import manquant

# --- Nouveaux Imports --- 
# Supprimer AsyncSession et Depends si plus utilisés directement
# from sqlalchemy.ext.asyncio import AsyncSession
# from fastapi import Depends

# Configuration
from src.orders.config import (
    ALLOWED_ORDER_STATUS,
    ORDER_STATUS_DISPLAY,
    MAX_ITEMS_PER_ORDER,
    MIN_ORDER_AMOUNT,
    MAX_ORDER_AMOUNT
)

# Repositories (Interfaces)
# Conserver l'import de l'interface pour le type hint
from src.orders.interfaces.repositories import AbstractOrderRepository
# from src.products.domain.repositories import AbstractProductVariantRepository, AbstractStockRepository
# from src.addresses.domain.repositories import AbstractAddressRepository # Pour valider adresses

# Entités du Domaine - Moins utilisées directement si le repo retourne des ORM
# from src.orders.domain.entities import OrderEntity, OrderItemEntity

# Schémas API (depuis le nouveau module models)
from src.orders.models import (
    Order, OrderCreate, OrderResponse, OrderUpdate, OrderRead,
    OrderItemCreate, OrderItemResponse
)

# Supprimer l'import de .crud
# from . import crud as order_crud

# Services ou CRUDs des autres modules (Conserver pour l'injection)
from src.addresses.service import AddressService
from src.products.application.services import ProductVariantService
from src.stock.services import StockService # Injecter StockService

# Exceptions
from orders.exceptions import (
    OrderNotFoundException, InvalidOrderStatusException, 
    OrderUpdateForbiddenException, OrderCreationFailedException
)
from src.products.domain.exceptions import (
    VariantNotFoundException, InsufficientStockException, StockNotFoundException
)
# Utiliser directement HTTPException pour les erreurs d'adresse ici ou définir des exceptions applicatives dédiées
# from ...addresses.domain.exceptions import AddressNotFoundException
from src.products.domain.exceptions import InvalidOperationException # Autres erreurs

# --- Service Email --- 
from src.email.services import EmailService # Importer le service email

logger = logging.getLogger(__name__)

class OrderService:
    """Service applicatif pour la gestion des commandes (refactorisé avec Repository)."""

    def __init__(self, 
                 # Remplacer db par order_repository
                 order_repository: AbstractOrderRepository,
                 address_service: AddressService, 
                 email_service: EmailService, 
                 product_variant_service: ProductVariantService, 
                 stock_service: StockService
                 ):
        # Supprimer self.db
        # self.db = db
        self.order_repository = order_repository
        self.address_service = address_service
        self.email_service = email_service
        self.product_variant_service = product_variant_service
        self.stock_service = stock_service
        logger.info("OrderService initialisé avec OrderRepository, AddressService, EmailService, ProductVariantService, StockService.")

    # --- GET Methods --- 
    
    async def get_order(
        self, 
        order_id: int, 
        user_id: Optional[int] = None, 
        is_admin: bool = False
    ) -> OrderRead: # Retourner OrderRead directement
        """Récupère une commande par ID avec ses items via le repository, vérifiant l'accès utilisateur."""
        logger.debug(f"[OrderService] Récupération commande ID: {order_id} pour user: {user_id} (admin: {is_admin})")
        
        # Utiliser la méthode du repo qui retourne le schéma Read
        order = await self.order_repository.get_by_id_as_read_schema(order_id)
        
        if not order:
            logger.warning(f"[OrderService] Commande ID {order_id} non trouvée via repository.")
            raise OrderNotFoundException(order_id=order_id)
        
        # La vérification d'accès reste dans le service
        if not is_admin and user_id is not None and order.user_id != user_id:
            logger.warning(f"[OrderService] Accès refusé commande {order_id} pour user {user_id}.")
            # Lever l'exception ici pour masquer l'existence de la commande
            raise OrderNotFoundException(order_id=order_id)
            
        return order

    async def list_user_orders(self, user_id: int, limit: int, offset: int) -> Tuple[List[OrderRead], int]:
        """Liste les commandes pour un utilisateur spécifique via le repository."""
        logger.debug(f"[OrderService] Listage commandes pour user ID: {user_id}, limit: {limit}, offset: {offset}")
        
        # Utiliser la méthode list_by_user du repository
        return await self.order_repository.list_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
    # --- CREATE Method --- 
    async def create_order(self, order_data: OrderCreate, requesting_user_id: int) -> OrderRead:
        """Crée une nouvelle commande via le repository après validation métier."""
        logger.info(f"[OrderService] Tentative création commande pour user ID: {requesting_user_id}")
        if order_data.user_id != requesting_user_id:
             logger.warning(f"[OrderService] Incohérence user ID création commande (demandeur: {requesting_user_id}, payload: {order_data.user_id}). Utilisation ID demandeur.")
             order_data.user_id = requesting_user_id
             
        if not order_data.items:
             logger.error("[OrderService] Tentative de création de commande sans articles.")
             raise InvalidOperationException("Impossible de créer une commande sans articles.")

        # 1. Valider les adresses via AddressService
        try:
            await self.address_service.validate_address_ownership(order_data.delivery_address_id, requesting_user_id)
            await self.address_service.validate_address_ownership(order_data.billing_address_id, requesting_user_id)
            logger.debug(f"[OrderService] Adresses {order_data.delivery_address_id} et {order_data.billing_address_id} validées pour user {requesting_user_id}.")
        except HTTPException as e:
            logger.error(f"[OrderService] Erreur validation adresse pour user {requesting_user_id}: {e.detail}")
            if e.status_code == 404:
                 raise OrderCreationFailedException(f"Adresse ID {order_data.delivery_address_id if 'delivery' in e.detail.lower() else order_data.billing_address_id} invalide ou non trouvée.")
            elif e.status_code == 403:
                 raise OrderUpdateForbiddenException("L'adresse fournie n'appartient pas à l'utilisateur.")
            else:
                 raise OrderCreationFailedException(f"Erreur lors de la validation de l'adresse: {e.detail}")
        except Exception as e:
             logger.exception(f"[OrderService] Erreur inattendue validation adresse: {e}")
             raise OrderCreationFailedException("Erreur interne lors de la validation de l'adresse.")
            
        validated_items_data_for_repo = []
        calculated_total = Decimal(0)
        stock_decrements: Dict[int, int] = {} # variant_id -> quantity_to_decrement
        item_details_for_email = []

        # 2. Valider chaque item, vérifier le stock et préparer les données
        try:
            variant_ids = [item.product_variant_id for item in order_data.items]
            variants_map = await self.product_variant_service.get_variants_details(variant_ids)

            for item_in in order_data.items:
                variant_details = variants_map.get(item_in.product_variant_id)
                if not variant_details:
                    raise VariantNotFoundException(variant_id=item_in.product_variant_id) 
                
                stock_info = await self.stock_service.get_stock_for_variant(product_variant_id=item_in.product_variant_id)
                if not stock_info:
                     logger.error(f"[OrderService] Incohérence: Stock non trouvé pour variant ID {item_in.product_variant_id} existante via StockService.")
                     raise StockNotFoundException(variant_id=item_in.product_variant_id)

                current_stock = stock_info.quantity
                
                if current_stock < item_in.quantity:
                    logger.warning(f"[OrderService] Stock insuffisant pour variant ID {item_in.product_variant_id}. Demandé: {item_in.quantity}, Disponible: {current_stock}")
                    raise InsufficientStockException(item_in.product_variant_id, item_in.quantity, current_stock)
                
                current_price = getattr(variant_details, 'price', None)
                if current_price is None:
                     logger.error(f"Prix non trouvé pour la variante ID {item_in.product_variant_id} via ProductVariantService.")
                     raise OrderCreationFailedException(f"Impossible de déterminer le prix pour le produit ID {item_in.product_variant_id}.")
                     
                current_price_decimal = Decimal(str(current_price)) 
                item_total = current_price_decimal * item_in.quantity
                calculated_total += item_total
                
                # Préparer les données pour la méthode create_order_with_items du repo
                validated_items_data_for_repo.append({
                    "product_variant_id": item_in.product_variant_id,
                    "quantity": item_in.quantity,
                    "price_at_order": current_price_decimal
                })
                stock_decrements[item_in.product_variant_id] = stock_decrements.get(item_in.product_variant_id, 0) + item_in.quantity
                
                item_details_for_email.append({
                     "variant_sku": getattr(variant_details, 'sku', 'N/A'),
                     "variant_name": getattr(variant_details, 'name', 'Produit inconnu'), 
                     "quantity": item_in.quantity,
                     "price_at_order": current_price_decimal,
                })
                
        except VariantNotFoundException as e:
             logger.error(f"[OrderService] Variante {e.variant_id} non trouvée lors création commande.")
             raise OrderCreationFailedException(f"Produit ID {e.variant_id} non trouvé ou indisponible.")
        except InsufficientStockException as e:
             variant_name = getattr(variants_map.get(e.variant_id), 'name', f'ID {e.variant_id}')
             logger.error(f"[OrderService] Stock insuffisant pour variante {e.variant_id} ({variant_name}) (demandé: {e.requested}, dispo: {e.available}).")
             raise OrderCreationFailedException(f"Stock insuffisant pour le produit '{variant_name}'. Demandé: {e.requested}, Disponible: {e.available}.")
        except StockNotFoundException as e:
            logger.error(f"[OrderService] Erreur interne: Stock non trouvé pour variante {e.variant_id} lors création commande via StockService.")
            raise OrderCreationFailedException(f"Erreur de stock interne pour produit ID {e.variant_id}. Veuillez contacter le support.")
        except Exception as e:
             logger.exception(f"[OrderService] Erreur inattendue pendant la validation des items: {e}")
             raise OrderCreationFailedException(f"Erreur interne lors de la validation des produits: {e}")


        # 3. Préparer les données finales pour l'Order
        order_create_data_for_repo = {
            "user_id": order_data.user_id,
            "status": order_data.status or "pending",
            "total_amount": calculated_total,
            "delivery_address_id": order_data.delivery_address_id,
            "billing_address_id": order_data.billing_address_id,
            "order_date": datetime.utcnow()
        }

        created_order_orm = None
        try:
            # 4. Appeler le repository pour créer la commande et les items
            # Cette méthode devrait gérer la transaction pour Order et OrderItems
            created_order_orm = await self.order_repository.create_order_with_items(
                order_data=order_create_data_for_repo,
                items_data=validated_items_data_for_repo
            )
            # Pas besoin de flush/refresh ici, le repo s'en charge et retourne l'ORM complet

            logger.info(f"[OrderService] Commande ID {created_order_orm.id} créée via repository pour user {order_data.user_id}.")

            # 5. Décrémenter le stock via StockService (après succès de la création commande)
            stock_update_tasks = []
            for variant_id, quantity_to_decrement in stock_decrements.items():
                 stock_update_tasks.append(
                     self.stock_service.update_stock_quantity(
                         product_variant_id=variant_id, 
                         quantity_change=-quantity_to_decrement
                     )
                 )
            
            stock_update_results = await asyncio.gather(*stock_update_tasks, return_exceptions=True)
            
            failed_stock_updates = [res for res in stock_update_results if isinstance(res, Exception)]
            if failed_stock_updates:
                 first_error = failed_stock_updates[0]
                 logger.error(f"[OrderService] Échec MAJ stock via StockService après création commande {created_order_orm.id}: {first_error}")
                 # Logique de compensation possible ici (ex: annuler la commande, notifier admin)
                 # Pour l'instant, on lève une exception pour indiquer le problème
                 raise OrderCreationFailedException(f"La commande {created_order_orm.id} a été créée, mais la mise à jour du stock a échoué: {first_error}")

            # 6. Envoyer l'email de confirmation (après succès stock)
            try:
                # Récupérer email utilisateur (nécessite peut-être un UserService ou accès User)
                # Pour l'exemple, on suppose un user_email disponible
                # user_email = await self.get_user_email(order_data.user_id)
                user_email = "test@example.com" # Placeholder
                await self.email_service.send_order_confirmation(
                    to_email=user_email,
                    order_id=created_order_orm.id,
                    order_date=created_order_orm.order_date,
                    total_amount=created_order_orm.total_amount,
                    items=item_details_for_email
                    # Ajouter adresses si nécessaire
                )
                logger.info(f"[OrderService] Email confirmation envoyé pour commande ID {created_order_orm.id}")
            except Exception as e:
                # Logguer l'erreur d'email mais ne pas annuler la commande
                logger.error(f"[OrderService] Erreur envoi email confirmation commande {created_order_orm.id}: {e}", exc_info=True)

            # 7. Retourner le schéma Read de la commande créée
            # Re-fetch avec le schema pour s'assurer que toutes les relations sont chargées
            return await self.order_repository.get_by_id_as_read_schema(created_order_orm.id)

        except OrderCreationFailedException as e:
            logger.error(f"[OrderService] Échec création commande (repo error): {e}", exc_info=True)
            raise
        except Exception as e:
            logger.exception(f"[OrderService] Erreur inattendue lors de la création de la commande via repository: {e}")
            # Essayer de lever une exception plus spécifique si possible
            raise OrderCreationFailedException(f"Erreur interne inattendue lors de la création de la commande: {e}")

    # --- UPDATE Method ---
    async def update_order_status(self, order_id: int, status_update: OrderUpdate, requesting_user_id: int, is_admin: bool) -> OrderRead:
        """Met à jour le statut d'une commande via le repository après validation métier."""
        logger.info(f"[OrderService] Tentative MAJ statut commande ID: {order_id} vers '{status_update.status}' par user: {requesting_user_id} (admin: {is_admin})")

        new_status = status_update.status
        if new_status not in ALLOWED_ORDER_STATUS:
            raise InvalidOrderStatusException(new_status)

        # 1. Récupérer la commande existante (ORM pour vérifier l'état actuel)
        order = await self.order_repository.get_by_id(order_id)
        if not order:
            raise OrderNotFoundException(order_id)

        # 2. Vérifier les permissions
        if not is_admin and order.user_id != requesting_user_id:
            logger.warning(f"[OrderService] Accès refusé MAJ statut commande {order_id} pour user {requesting_user_id}.")
            raise OrderUpdateForbiddenException("Vous ne pouvez pas modifier cette commande.")
        
        # Ajouter logique métier ici: Peut-on passer de order.status à new_status ?
        # Exemple simple: on ne peut pas revenir en arrière depuis 'shipped' ou 'cancelled'
        if order.status in ["shipped", "cancelled"] and new_status != order.status:
             logger.warning(f"[OrderService] MAJ statut interdite de '{order.status}' vers '{new_status}' pour commande {order_id}.")
             raise InvalidOrderStatusException(f"Impossible de changer le statut de '{ORDER_STATUS_DISPLAY.get(order.status, order.status)}' à '{ORDER_STATUS_DISPLAY.get(new_status, new_status)}'.")

        # 3. Appeler le repository pour mettre à jour le statut
        try:
            updated_order_orm = await self.order_repository.update_order_status(order_id, new_status)
            if not updated_order_orm: # Double check si le repo ne lève pas NotFound
                 raise OrderNotFoundException(order_id) 
                 
            logger.info(f"[OrderService] Statut commande ID {order_id} mis à jour vers '{new_status}'.")
            
            # Envoyer email de notification de changement de statut ?
            try:
                 # user_email = await self.get_user_email(order.user_id)
                 user_email = "test@example.com" # Placeholder
                 await self.email_service.send_status_update_notification(
                     to_email=user_email,
                     order_id=order_id,
                     new_status=ORDER_STATUS_DISPLAY.get(new_status, new_status)
                 )
                 logger.info(f"[OrderService] Email notification MAJ statut envoyé pour commande {order_id}")
            except Exception as e:
                logger.error(f"[OrderService] Erreur envoi email notification MAJ statut commande {order_id}: {e}", exc_info=True)

            # 4. Retourner le schéma Read de la commande mise à jour
            # Re-fetch avec le schema pour s'assurer que toutes les relations sont chargées
            return await self.order_repository.get_by_id_as_read_schema(order_id)

        except OrderNotFoundException:
            raise # Re-lever
        except Exception as e:
            logger.error(f"[OrderService] Erreur lors de la MAJ statut commande {order_id} via repository: {e}", exc_info=True)
            raise OrderUpdateForbiddenException(f"Erreur interne lors de la mise à jour du statut: {e}")

    # --- DELETE Method (Optional) ---
    # async def delete_order(self, order_id: int, requesting_user_id: int, is_admin: bool):
    #     logger.info(f"[OrderService] Tentative suppression commande ID: {order_id}")
    #     order = await self.order_repository.get_by_id(order_id)
    #     if not order:
    #         raise OrderNotFoundException(order_id)
        
    #     if not is_admin and order.user_id != requesting_user_id:
    #         raise OrderUpdateForbiddenException("Suppression non autorisée.")
            
    #     # Logique métier: Peut-on supprimer une commande dans son état actuel?
    #     if order.status not in ["pending", "cancelled"]:
    #          raise InvalidOperationException(f"Impossible de supprimer une commande avec le statut '{order.status}'.")
             
    #     # Attention: La suppression physique est rarement une bonne idée pour les commandes.
    #     # Préférer un statut 'deleted' ou 'archived'.
    #     # await self.order_repository.delete(order_id)
    #     # logger.info(f"Commande ID {order_id} supprimée (si implémenté).")
    #     raise NotImplementedError("La suppression physique des commandes n'est pas implémentée.")