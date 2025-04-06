import logging
import json
from typing import Optional, List, Dict, Any
from decimal import Decimal
import os # Pour vérifier existence PDF

# Domaine LLM
from src.llm.domain.llm_interface import AbstractLLM
from src.llm.domain import prompt_templates
from src.llm.application.schemas import ParsedIntent, RequestedItem

# --- NOUVELLES DÉPENDANCES (via injection) ---
from src.products.domain.repositories import (
    AbstractProductVariantRepository, AbstractStockRepository
)
# Exceptions spécifiques si besoin de les attraper ici
from src.products.domain.exceptions import VariantNotFoundException, StockNotFoundException 

# --- NOUVEAU: Importer QuoteService --- 
from src.quotes.application.services import QuoteService
from src.quotes.domain.exceptions import QuoteNotFoundException
# -----------------------------------

# --- NOUVEAU: Importer EmailService --- 
from src.email.application.services import EmailService
# -----------------------------------

# --- NOUVEAU: Importer PDFService --- 
from src.pdf.application.services import PDFService # <-- Injecter PDFService
# -----------------------------------

# --- NOUVEAU: Importer OrderService --- 
from src.orders.application.services import OrderService # <-- Importer OrderService
from src.orders.application.schemas import OrderCreate, OrderItemCreate # <-- Importer schémas Order
from src.orders.domain.exceptions import OrderCreationFailedException # Import exceptions si besoin
from src.addresses.domain.repositories import AbstractAddressRepository # <-- Importer Address Repo Interface
from src.addresses.domain.exceptions import AddressNotFoundException # <-- Importer exception adresse
# -----------------------------------

# --- DÉPENDANCES TEMPORAIRES RESTANTES --- 
# !! ATTENTION: CECI EST TEMPORAIRE ET DOIT ÊTRE REMPLACÉ !!
from src.users.domain.user_entity import UserEntity # Pour typer l'utilisateur
# !! FIN SECTION TEMPORAIRE !!

# Exceptions FastAPI (pour l'instant, utilisées directement)
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class ChatService:
    """Service pour gérer la logique du chat IA."""

    def __init__(
        self,
        llm: AbstractLLM,
        # --- Injecter les repositories/services nécessaires ---
        variant_repo: AbstractProductVariantRepository,
        stock_repo: AbstractStockRepository,
        quote_service: QuoteService,
        email_service: EmailService, # <-- Injecter EmailService
        pdf_service: PDFService, # <-- Injecter PDFService
        order_service: OrderService, # <-- Injecter OrderService
        # ----------------------------------------------------
        # --- !! TEMPORAIRE: Ajouter les autres dépendances !! ---
        # address_repo: AbstractAddressRepository,
    ):
        self.llm = llm
        self.variant_repo = variant_repo
        self.stock_repo = stock_repo
        self.quote_service = quote_service
        self.email_service = email_service # <-- Assignation
        self.pdf_service = pdf_service # <-- Assignation
        self.order_service = order_service # <-- Assignation
        # ... assigner les autres dépendances

    async def handle_chat(self, user_input: str, current_user: Optional[UserEntity], selected_model: str) -> str:
        """Gère une requête de chat complète: parsing, traitement, génération."""
        user_id_for_log = current_user.id if current_user else "Anonyme"
        logger.info(f"[ChatService] Traitement requête: user={user_id_for_log}, model={selected_model}, input='{user_input}'")

        # --- Étape 1 : Parsing de l'intention --- 
        parsed_intent = await self._parse_user_intent(user_input)

        # --- Étape 2 : Traitement basé sur l'intention --- 
        response_message, should_call_llm, prompt_template, prompt_vars = await self._process_intent(
            parsed_intent, user_input, current_user
        )

        # --- Étape 3 : Génération de la réponse finale --- 
        if should_call_llm:
            try:
                final_formatted_prompt = prompt_template.format(**prompt_vars)
                logger.debug(f"[ChatService] Appel LLM final avec prompt: {final_formatted_prompt}")
                llm_response = await self.llm.invoke(final_formatted_prompt)
                response_message = llm_response # .strip() est déjà dans l'implémentation invoke
                logger.info(f"[ChatService] Réponse finale LLM générée pour user={user_id_for_log}")
            except Exception as e:
                logger.error(f"[ChatService] Erreur génération réponse finale LLM: {e}", exc_info=True)
                response_message = "Désolé, une erreur interne est survenue lors de la génération de la réponse."
        elif not response_message:
            logger.error("[ChatService] Erreur logique: should_call_llm=False mais response_message vide.")
            response_message = "Désolé, une erreur interne est survenue."

        return response_message

    async def _parse_user_intent(self, user_input: str) -> ParsedIntent:
        """Utilise le LLM pour parser l'intention et les entités de l'input utilisateur."""
        try:
            parsing_formatted_prompt = prompt_templates.parsing_prompt.format(input=user_input)
            logger.debug("[ChatService] Appel LLM (parsing)...")
            parsing_response_raw = await self.llm.invoke(parsing_formatted_prompt)
            logger.debug(f"[ChatService] Réponse brute parsing: {parsing_response_raw}")
            
            # Nettoyage potentiel de la réponse JSON
            json_str = parsing_response_raw.strip().strip('```json').strip('```').strip()
            parsed_data = json.loads(json_str)
            
            # Validation avec le schéma Pydantic
            parsed_intent = ParsedIntent.model_validate(parsed_data)
            logger.info(f"[ChatService] Parsing LLM réussi: intent={parsed_intent.intent}, items={len(parsed_intent.items)}")
            return parsed_intent
        except json.JSONDecodeError as e:
            logger.error(f"[ChatService] Erreur décodage JSON parsing: {e}")
        except Exception as e:
            logger.error(f"[ChatService] Erreur inattendue parsing LLM: {e}", exc_info=True)
        
        # En cas d'erreur, retourner une intention générale
        logger.warning("[ChatService] Échec parsing, retour à info_generale.")
        return ParsedIntent(intent="info_generale", items=[])

    async def _process_intent(self, parsed_intent: ParsedIntent, user_input: str, current_user: Optional[UserEntity]) -> tuple[str, bool, Any, Dict]:
        """Traite l'intention parsée et prépare la réponse ou le prompt final."""
        intent = parsed_intent.intent
        items_requested = parsed_intent.items
        response_message = ""
        should_call_llm = True
        final_prompt = prompt_templates.general_chat_prompt
        prompt_input_vars = {"input": user_input}

        if intent == "info_generale" or intent == "salutation":
            logger.debug(f"[ChatService] Traitement intention: {intent}")
            # Utilise le prompt général par défaut

        elif intent == "demande_produits":
            logger.debug(f"[ChatService] Traitement intention: {intent}")
            if not items_requested:
                logger.warning("[ChatService] Intention 'demande_produits' sans items.")
                response_message = "Je vois que vous cherchez des infos produits, mais je n'ai pas saisi lesquels. Pouvez-vous préciser (référence SKU ou description) ?"
                should_call_llm = False
            else:
                stock_summary = "\nInformations produits:\n"
                variant_details_list = [] # Pour stocker les détails pour le prompt
                for item_dto in items_requested:
                    sku = item_dto.sku
                    if sku:
                        try:
                            variant = await self.variant_repo.get_by_sku(sku=sku)
                            if variant:
                                stock_info = await self.stock_repo.get_for_variant(variant_id=variant.id)
                                stock_level = stock_info.quantity if stock_info else 0
                                details = f"- Réf {sku} ({variant.name}): Stock={stock_level}, Prix={variant.price:.2f} €"
                                stock_summary += details + "\n"
                                variant_details_list.append({"sku": sku, "name": variant.name, "stock": stock_level, "price": variant.price})
                            else:
                                stock_summary += f"- Réf {sku}: Inconnue.\n"
                        except Exception as repo_error: 
                             logger.error(f"[ChatService] Erreur repo lors recherche SKU {sku}: {repo_error}", exc_info=True)
                             stock_summary += f"- Réf {sku}: Erreur lors de la recherche.\n"
                    else:
                        stock_summary += f"- Produit '{item_dto.base_product or 'inconnu'}': Précisez la référence (SKU).\n"
                
                # Mettre à jour les variables pour le prompt de stock
                prompt_input_vars["stock_summary"] = stock_summary 
                # Passer aussi une version structurée si le template le gère
                # prompt_input_vars["variant_details"] = variant_details_list
                final_prompt = prompt_templates.stock_prompt # Utiliser le template dédié

        elif intent == "creer_devis":
            logger.debug(f"[ChatService] Traitement intention: {intent}")
            should_call_llm = False
            if not current_user:
                response_message = "Pour créer un devis, veuillez vous connecter ou créer un compte."
            elif not items_requested:
                response_message = "Je peux créer un devis, mais spécifiez d'abord les produits (SKU) et quantités."
            else:
                response_message = await self._handle_quote_creation(current_user, items_requested)

        elif intent == "passer_commande":
            logger.debug(f"[ChatService] Traitement intention: {intent}")
            should_call_llm = False
            if not current_user:
                response_message = "Pour commander, veuillez vous connecter ou créer un compte."
            elif not items_requested:
                response_message = "Je peux passer commande, mais spécifiez d'abord les produits (SKU) et quantités."
            else:
                 response_message = await self._handle_order_creation(current_user, items_requested)

        else:
            logger.warning(f"[ChatService] Intention inconnue '{intent}', traitement comme info_generale.")
            # Utilise le prompt général par défaut

        return response_message, should_call_llm, final_prompt, prompt_input_vars

    async def _handle_quote_creation(self, current_user: UserEntity, items_requested: List[RequestedItem]) -> str:
        """Gère la logique de création de devis."""
        quote_items_to_create = [] # Utilise OrderItemCreate (qui devrait être compatible)
        not_found_skus = []
        invalid_items = []
        item_details_for_email_and_pdf = [] # Pour email et PDF
        try:
            # 1. Valider les items et récupérer les infos variantes
            for item_dto in items_requested:
                sku = item_dto.sku
                quantity = item_dto.quantity
                if not sku or quantity <= 0:
                    invalid_items.append(item_dto.model_dump(exclude_unset=True))
                    continue
                
                variant = await self.variant_repo.get_by_sku(sku=sku)
                if not variant:
                    not_found_skus.append(sku)
                else:
                    item_price = variant.price
                    quote_items_to_create.append(
                        OrderItemCreate( # Utiliser OrderItemCreate ici aussi
                            product_variant_id=variant.id,
                            quantity=quantity,
                            unit_price=item_price # Le service Quote calculera le total
                        )
                    )
                    # Ajouter détails pour email/PDF
                    item_details_for_email_and_pdf.append({
                        "variant_sku": variant.sku,
                        "quantity": quantity,
                        "price_at_quote": item_price,
                        "variant_details": { "name": variant.name }
                    })
            
            if invalid_items: return f"Articles invalides: {invalid_items}."
            if not_found_skus: return f"Produits non trouvés: {', '.join(not_found_skus)}."
            if not quote_items_to_create: return "Aucun produit valide reconnu."

            # 2. Préparer le DTO de création pour QuoteService
            # On adapte QuoteCreate pour prendre des OrderItemCreate
            quote_to_create_dto = {
                 "user_id": current_user.id,
                 "items": [item.model_dump() for item in quote_items_to_create] # Convertir en dict
            }
            
            created_quote_response = await self.quote_service.create_quote(
                quote_data=quote_to_create_dto, # Passer le dict
                requesting_user_id=current_user.id
            )
            response_message = f"Devis {created_quote_response.id} créé avec succès !"

            # 3. Tentative de génération PDF et envoi email
            await self._generate_and_send_quote_pdf(created_quote_response, current_user, item_details_for_email_and_pdf)
            return response_message

        except (VariantNotFoundException, QuoteNotFoundException) as e:
            logger.warning(f"[ChatService] Échec création devis pour user {current_user.id}: {e}")
            if isinstance(e, VariantNotFoundException):
                 return f"Le produit avec SKU {e.sku or e.variant_id} n'a pas été trouvé."
            return f"Erreur lors de la création du devis: {e}"
        except Exception as e:
            logger.error(f"[ChatService] Erreur inattendue création devis pour user {current_user.id}: {e}", exc_info=True)
            return "Désolé, une erreur interne est survenue lors de la création du devis."

    async def _handle_order_creation(self, current_user: UserEntity, items_requested: List[RequestedItem]) -> str:
        """Gère la logique de création de commande en utilisant OrderService."""
        logger.info(f"[ChatService] Tentative création commande pour user {current_user.id} via OrderService.")
        order_items_to_create: List[OrderItemCreate] = [] 
        not_found_skus = []
        invalid_items = []
        insufficient_stock = []

        try:
            # 1. Valider items et stock (similaire à la création de devis)
            for item_dto in items_requested:
                sku = item_dto.sku
                quantity = item_dto.quantity
                if not sku or quantity <= 0:
                    invalid_items.append(item_dto.model_dump(exclude_unset=True))
                    continue
                
                variant = await self.variant_repo.get_by_sku(sku=sku)
                if not variant:
                    not_found_skus.append(sku)
                    continue
                    
                # Vérifier stock (le OrderService le refera, mais bonne pratique de vérifier avant)
                stock_info = await self.stock_repo.get_for_variant(variant_id=variant.id)
                current_stock = stock_info.quantity if stock_info else 0
                if current_stock < quantity:
                    insufficient_stock.append(f"{sku} (demandé: {quantity}, dispo: {current_stock})")
                    continue
                
                # Utiliser le schéma OrderItemCreate du domaine orders
                order_items_to_create.append(
                    OrderItemCreate(
                        product_variant_id=variant.id,
                        quantity=quantity,
                        # Le prix unitaire sera fixé par OrderService au moment de la création
                        # en se basant sur le prix actuel de la variante.
                        # On pourrait le pré-calculer ici pour estimation, mais ce n'est pas nécessaire
                        # pour le DTO OrderCreate.
                    )
                )

            # 2. Retourner erreurs si trouvées lors de la validation initiale
            if invalid_items: return f"Articles invalides pour la commande: {invalid_items}."
            if not_found_skus: return f"Produits non trouvés pour la commande: {', '.join(not_found_skus)}."
            if insufficient_stock: return f"Stock insuffisant pour: {', '.join(insufficient_stock)}."
            if not order_items_to_create: return "Aucun produit valide reconnu pour la commande."

            # 3. Obtenir l'adresse de livraison par défaut via AddressRepository
            try:
                default_address = await self.address_repo.get_default_address(user_id=current_user.id)
                if not default_address:
                     return "Veuillez définir une adresse de livraison par défaut dans votre profil avant de commander."
            except AddressNotFoundException:
                 # Gérer le cas où l'utilisateur n'a PAS d'adresse du tout (get_default pourrait retourner None)
                 return "Aucune adresse trouvée. Veuillez ajouter une adresse et la définir par défaut."
            except Exception as addr_err:
                logger.error(f"[ChatService] Erreur récupération adresse défaut user {current_user.id}: {addr_err}", exc_info=True)
                return "Erreur lors de la récupération de votre adresse par défaut."
            
            # 4. Créer le DTO OrderCreate
            order_to_create = OrderCreate(
                user_id=current_user.id,
                delivery_address_id=default_address.id,
                billing_address_id=default_address.id, # Utiliser la même pour l'instant
                items=order_items_to_create
                # status peut être omis, OrderService utilisera "pending" par défaut
            )

            # 5. Appeler OrderService pour créer la commande
            # OrderService gère la validation finale, la décrémentation atomique du stock,
            # et l'envoi de l'email de confirmation.
            created_order = await self.order_service.create_order(
                order_data=order_to_create,
                requesting_user_id=current_user.id
            )

            return f"Commande {created_order.id} créée avec succès ! Vous recevrez une confirmation par email."
        
        # Gérer les exceptions spécifiques levées par OrderService ou les repos
        except (AddressNotFoundException, VariantNotFoundException, InsufficientStockException, OrderCreationFailedException) as e:
             logger.warning(f"[ChatService] Échec création commande pour user {current_user.id}: {e}")
             # Retourner un message d'erreur plus ciblé
             return f"Impossible de créer la commande : {e}" 
        except Exception as e:
            logger.error(f"[ChatService] Erreur inattendue création commande user {current_user.id}: {e}", exc_info=True)
            return "Désolé, une erreur interne est survenue lors de la tentative de commande."

    # --- Méthodes utilitaires (potentiellement à déplacer/refactoriser) ---

    async def _generate_and_send_quote_pdf(self, quote_response, current_user: UserEntity, item_details: List[Dict[str, Any]]):
        """Génère le PDF du devis et l'envoie par email."""
        quote_id = quote_response.id
        logger.info(f"[ChatService] Tentative génération PDF et envoi email pour devis {quote_id}")
        pdf_content: Optional[bytes] = None
        
        try:
            # --- Préparer les données pour le PDF --- 
            quote_data_for_pdf = {
                "id": quote_response.id,
                "status": quote_response.status,
                "created_at": quote_response.created_at,
                "total_amount": quote_response.total_amount,
                "user": {"id": current_user.id, "name": current_user.name, "email": current_user.email},
                "items": item_details,
                # Adresses non présentes dans QuoteResponse, à récupérer si nécessaire
                "delivery_address": None, 
                "billing_address": None 
            }
            
            # --- MODIFIÉ: Utilisation de PDFService --- 
            pdf_content = await self.pdf_service.generate_quote_pdf_from_data(quote_data_for_pdf)
            logger.info(f"[ChatService] PDF devis {quote_id} généré en mémoire.")
            # --- FIN MODIFICATION --- 
            
        except QuoteNotFoundException:
             logger.error(f"[ChatService] Devis {quote_id} non trouvé lors de la tentative de génération PDF.")
             return # Ne pas continuer si devis non trouvé
        except Exception as pdf_err:
             logger.error(f"[ChatService] Erreur lors de la génération PDF devis {quote_id}: {pdf_err}", exc_info=True)
             # Continuer pour envoyer l'email sans PDF ? Pour l'instant oui.
        
        # --- Envoi email (avec ou sans PDF) --- 
        try:
             pdf_filename = f"devis_{quote_id}.pdf" if pdf_content else None
             quote_details_for_email = {
                "id": quote_response.id,
                "user_name": current_user.name,
                "total_amount": quote_response.total_amount,
                "items": item_details
             }
             logger.info(f"[ChatService] Tentative envoi email devis {quote_id} à {current_user.email}")
             success = await self.email_service.send_quote_details_email(
                 recipient_email=current_user.email,
                 quote_details=quote_details_for_email,
                 pdf_content=pdf_content, # Sera None si la génération a échoué
                 pdf_filename=pdf_filename
             )
             if success:
                 logger.info(f"[ChatService] Email devis {quote_id} envoyé (PDF: {'Oui' if pdf_content else 'Non'}).")
             else:
                 logger.warning(f"[ChatService] Échec envoi email devis {quote_id} (retour service: False).")
                 
        except Exception as email_err:
             logger.error(f"[ChatService] Erreur lors de l'envoi email devis {quote_id}: {email_err}", exc_info=True)
