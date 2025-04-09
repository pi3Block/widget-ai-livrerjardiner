"""
Service de gestion des interactions LLM.

Ce module implémente la logique métier principale pour :
- Le traitement des requêtes de chat
- Le parsing des intentions utilisateur
- La gestion des devis et commandes via LLM
- La génération et l'envoi de documents

Classes:
    ChatService: Service principal gérant les interactions LLM
"""
import logging
import json
from typing import Dict, List, Optional, Any

# Interfaces et modèles du domaine LLM
from src.llm.interfaces import (
    AbstractProductVariantRepository,
    AbstractStockRepository,
    AbstractAddressRepository
)
from src.llm.llm_interface import AbstractLLM
from src.llm.models import ParsedIntent, RequestedItem
from src.llm import templates

# Imports des autres domaines
from src.users.models import User
# Services externes
from src.quotes.service import QuoteService
from src.email.services import EmailService
from src.pdf.service import PDFService
from src.orders.service import OrderService

# Modèles et DTOs
from src.orders.models import OrderCreate, OrderItemCreate

# Exceptions
from src.product_variants.exceptions import VariantNotFoundException
from src.stock.exceptions import StockNotFoundError
from src.quotes.exceptions import QuoteNotFoundException
from src.orders.exceptions import (
    OrderCreationFailedException,
    InsufficientStockException
)
from src.addresses.exceptions import AddressNotFoundException

# Ajouter les imports des nouvelles exceptions
from src.llm.exceptions import (
    LLMError,
    LLMParsingError,
    LLMRequestError,
    LLMTimeoutError,
    InvalidIntentError,
    QuoteCreationError,
    OrderCreationError
)

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service pour gérer la logique du chat IA.
    
    Ce service est responsable de :
    - Traiter les requêtes de chat des utilisateurs
    - Parser les intentions et entités via LLM
    - Gérer les interactions avec les produits, stocks, devis et commandes
    - Coordonner la génération et l'envoi de documents
    
    Attributes:
        llm: Interface d'accès au modèle de langage
        variant_repo: Repository pour les variantes de produits
        stock_repo: Repository pour la gestion des stocks
        quote_service: Service de gestion des devis
        email_service: Service d'envoi d'emails
        pdf_service: Service de génération de PDFs
        order_service: Service de gestion des commandes
        address_repo: Repository pour les adresses
    """

    def __init__(
        self,
        llm: AbstractLLM,
        variant_repo: AbstractProductVariantRepository,
        stock_repo: AbstractStockRepository,
        quote_service: QuoteService,
        email_service: EmailService,
        pdf_service: PDFService,
        order_service: OrderService,
        address_repo: AbstractAddressRepository,
    ):
        """
        Initialise le service avec ses dépendances.

        Args:
            llm: Interface d'accès au modèle de langage
            variant_repo: Repository pour les variantes de produits
            stock_repo: Repository pour la gestion des stocks
            quote_service: Service de gestion des devis
            email_service: Service d'envoi d'emails
            pdf_service: Service de génération de PDFs
            order_service: Service de gestion des commandes
            address_repo: Repository pour les adresses
        """
        self.llm = llm
        self.variant_repo = variant_repo
        self.stock_repo = stock_repo
        self.quote_service = quote_service
        self.email_service = email_service
        self.pdf_service = pdf_service
        self.order_service = order_service
        self.address_repo = address_repo

    async def handle_chat(self, user_input: str, current_user: Optional[User], selected_model: str) -> str:
        """
        Gère une requête de chat complète: parsing, traitement, génération.
        
        Args:
            user_input: Le texte de l'utilisateur à traiter
            current_user: L'utilisateur courant ou None si anonyme
            selected_model: Le modèle LLM à utiliser
            
        Returns:
            str: La réponse générée pour l'utilisateur
            
        Raises:
            LLMError: Si une erreur survient lors de l'interaction avec le LLM
            QuoteCreationError: Si la création d'un devis échoue
            OrderCreationError: Si la création d'une commande échoue
        """
        user_id_for_log = current_user.id if current_user else "Anonyme"
        logger.info(f"[ChatService] Traitement requête: user={user_id_for_log}, model={selected_model}, input='{user_input}'")

        try:
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
                    response_message = llm_response
                    logger.info(f"[ChatService] Réponse finale LLM générée pour user={user_id_for_log}")
                except Exception as e:
                    logger.error(f"[ChatService] Erreur génération réponse finale LLM: {e}", exc_info=True)
                    raise LLMRequestError(
                        message="Erreur lors de la génération de la réponse",
                        status_code=getattr(e, 'status_code', None)
                    )
            elif not response_message:
                logger.error("[ChatService] Erreur logique: should_call_llm=False mais response_message vide.")
                raise LLMError("Erreur interne lors du traitement de la requête")

            return response_message

        except LLMError as e:
            # Propager les erreurs LLM spécifiques
            raise
        except Exception as e:
            # Convertir les autres erreurs en LLMError générique
            logger.error(f"[ChatService] Erreur inattendue: {e}", exc_info=True)
            raise LLMError(f"Une erreur inattendue est survenue: {str(e)}")

    async def _parse_user_intent(self, user_input: str) -> ParsedIntent:
        """
        Utilise le LLM pour parser l'intention et les entités de l'input utilisateur.
        
        Args:
            user_input: Le texte de l'utilisateur à parser
            
        Returns:
            ParsedIntent: L'intention et les entités parsées
            
        Raises:
            LLMParsingError: Si le parsing de l'intention échoue
        """
        try:
            parsing_formatted_prompt = templates.parsing_prompt.format(input=user_input)
            logger.debug("[ChatService] Appel LLM (parsing)...")
            parsing_response_raw = await self.llm.invoke(parsing_formatted_prompt)
            logger.debug(f"[ChatService] Réponse brute parsing: {parsing_response_raw}")
            
            # Nettoyage et parsing JSON
            json_str = parsing_response_raw.strip().strip('```json').strip('```').strip()
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                raise LLMParsingError(
                    message="Impossible de décoder la réponse JSON du LLM",
                    raw_response=parsing_response_raw
                ) from e
            
            # Validation avec le schéma Pydantic
            try:
                parsed_intent = ParsedIntent.model_validate(parsed_data)
            except Exception as e:
                raise LLMParsingError(
                    message="La réponse du LLM ne correspond pas au schéma attendu",
                    raw_response=parsing_response_raw
                ) from e
            
            logger.info(f"[ChatService] Parsing LLM réussi: intent={parsed_intent.intent}, items={len(parsed_intent.items)}")
            return parsed_intent
            
        except LLMParsingError:
            raise
        except Exception as e:
            logger.error(f"[ChatService] Erreur inattendue parsing LLM: {e}", exc_info=True)
            raise LLMParsingError(
                message="Erreur lors du parsing de l'intention",
                raw_response=getattr(e, 'response', None)
            ) from e

    async def _process_intent(self, parsed_intent: ParsedIntent, user_input: str, current_user: Optional[User]) -> tuple[str, bool, str, Dict[str, Any]]:
        """
        Traite l'intention parsée et prépare la réponse ou le prompt final.
        
        Args:
            parsed_intent: L'intention et les entités parsées
            user_input: Le texte original de l'utilisateur
            current_user: L'utilisateur courant ou None si anonyme
            
        Returns:
            tuple: (message_réponse, appeler_llm, template_prompt, variables_prompt)
            
        Raises:
            InvalidIntentError: Si l'intention n'est pas valide ou non gérée
            QuoteCreationError: Si la création d'un devis échoue
            OrderCreationError: Si la création d'une commande échoue
        """
        intent = parsed_intent.intent
        items_requested = parsed_intent.items
        response_message = ""
        should_call_llm = True
        final_prompt = templates.general_chat_prompt
        prompt_input_vars = {"input": user_input}

        try:
            if intent == "info_generale" or intent == "salutation":
                logger.debug(f"[ChatService] Traitement intention: {intent}")
                # Utilise le prompt général par défaut

            elif intent == "demande_produits":
                logger.debug(f"[ChatService] Traitement intention: {intent}")
                if not items_requested:
                    response_message = "Je vois que vous cherchez des infos produits, mais je n'ai pas saisi lesquels. Pouvez-vous préciser (référence SKU ou description) ?"
                    should_call_llm = False
                else:
                    stock_summary = await self._get_stock_summary(items_requested)
                    prompt_input_vars["stock_summary"] = stock_summary
                    final_prompt = templates.stock_prompt

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
                logger.warning(f"[ChatService] Intention inconnue '{intent}'")
                raise InvalidIntentError(intent, "Intention non reconnue")

            return response_message, should_call_llm, final_prompt, prompt_input_vars

        except (InvalidIntentError, QuoteCreationError, OrderCreationError):
            raise
        except Exception as e:
            logger.error(f"[ChatService] Erreur lors du traitement de l'intention {intent}: {e}", exc_info=True)
            raise LLMError(f"Erreur lors du traitement de votre demande: {str(e)}")

    async def _get_stock_summary(self, items_requested: List[RequestedItem]) -> str:
        """
        Génère un résumé des informations de stock pour les produits demandés.
        
        Args:
            items_requested: Liste des produits demandés
            
        Returns:
            str: Résumé formaté des informations de stock
            
        Raises:
            VariantNotFoundException: Si un produit n'est pas trouvé
            StockNotFoundError: Si les informations de stock sont inaccessibles
        """
        stock_summary = "\nInformations produits:\n"
        for item_dto in items_requested:
            sku = item_dto.sku
            if sku:
                try:
                    variant = await self.variant_repo.get_by_sku(sku=sku)
                    if not variant:
                        stock_summary += f"- Réf {sku}: Inconnue.\n"
                        continue
                        
                    stock_info = await self.stock_repo.get_for_variant(variant_id=variant.id)
                    stock_level = stock_info.quantity if stock_info else 0
                    details = f"- Réf {sku} ({variant.name}): Stock={stock_level}, Prix={variant.price:.2f} €"
                    stock_summary += details + "\n"
                    
                except (VariantNotFoundException, StockNotFoundError) as e:
                    logger.warning(f"[ChatService] Erreur accès produit/stock pour SKU {sku}: {e}")
                    stock_summary += f"- Réf {sku}: {str(e)}.\n"
                except Exception as e:
                    logger.error(f"[ChatService] Erreur inattendue pour SKU {sku}: {e}", exc_info=True)
                    stock_summary += f"- Réf {sku}: Erreur technique lors de la recherche.\n"
            else:
                stock_summary += f"- Produit '{item_dto.base_product or 'inconnu'}': Précisez la référence (SKU).\n"
                
        return stock_summary

    async def _handle_quote_creation(self, current_user: User, items_requested: List[RequestedItem]) -> str:
        """
        Gère la logique de création de devis.
        
        Args:
            current_user: L'utilisateur demandant le devis
            items_requested: Liste des produits pour le devis
            
        Returns:
            str: Message de confirmation ou d'erreur
            
        Raises:
            QuoteCreationError: Si la création du devis échoue
        """
        quote_items_to_create = []
        not_found_skus = []
        invalid_items = []
        item_details_for_email_and_pdf = []

        try:
            # 1. Valider les items et récupérer les infos variantes
            for item_dto in items_requested:
                if not self._validate_quote_item(item_dto):
                    invalid_items.append(item_dto.model_dump(exclude_unset=True))
                    continue

                try:
                    variant = await self.variant_repo.get_by_sku(sku=item_dto.sku)
                    quote_item = await self._create_quote_item(variant, item_dto)
                    quote_items_to_create.append(quote_item)
                    item_details_for_email_and_pdf.append(self._prepare_item_details(variant, item_dto))
                except VariantNotFoundException:
                    not_found_skus.append(item_dto.sku)

            if self._has_quote_errors(invalid_items, not_found_skus):
                error_message = self._format_quote_error_message(invalid_items, not_found_skus)
                raise QuoteCreationError(error_message, items_requested)

            # 2. Créer le devis
            created_quote = await self._create_quote(current_user, quote_items_to_create)
            
            # 3. Générer PDF et envoyer email
            await self._generate_and_send_quote_pdf(created_quote, current_user, item_details_for_email_and_pdf)
            
            return f"Devis {created_quote.id} créé avec succès !"

        except QuoteCreationError:
            raise
        except Exception as e:
            logger.error(f"[ChatService] Erreur inattendue création devis pour user {current_user.id}: {e}", exc_info=True)
            raise QuoteCreationError("Une erreur technique est survenue lors de la création du devis", items_requested)

    async def _handle_order_creation(self, current_user: User, items_requested: List[RequestedItem]) -> str:
        """
        Gère la logique de création de commande.
        
        Args:
            current_user: L'utilisateur passant la commande
            items_requested: Liste des produits à commander
            
        Returns:
            str: Message de confirmation ou d'erreur
            
        Raises:
            OrderCreationError: Si la création de la commande échoue
            AddressNotFoundException: Si l'adresse de livraison n'est pas trouvée
        """
        order_items_to_create: List[OrderItemCreate] = []
        not_found_skus = []
        invalid_items = []
        insufficient_stock = []

        try:
            # 1. Valider items et stock
            for item_dto in items_requested:
                if not self._validate_order_item(item_dto):
                    invalid_items.append(item_dto.model_dump(exclude_unset=True))
                    continue

                try:
                    variant = await self.variant_repo.get_by_sku(sku=item_dto.sku)
                    if not await self._check_stock_availability(variant.id, item_dto.quantity):
                        insufficient_stock.append(f"{item_dto.sku} (demandé: {item_dto.quantity})")
                        continue
                        
                    order_items_to_create.append(
                        OrderItemCreate(
                            product_variant_id=variant.id,
                            quantity=item_dto.quantity
                        )
                    )
                except VariantNotFoundException:
                    not_found_skus.append(item_dto.sku)

            if self._has_order_errors(invalid_items, not_found_skus, insufficient_stock):
                error_message = self._format_order_error_message(invalid_items, not_found_skus, insufficient_stock)
                raise OrderCreationError(error_message, items_requested)

            # 2. Récupérer l'adresse de livraison
            delivery_address = await self._get_delivery_address(current_user)

            # 3. Créer la commande
            order_to_create = OrderCreate(
                user_id=current_user.id,
                delivery_address_id=delivery_address.id,
                billing_address_id=delivery_address.id,
                items=order_items_to_create
            )

            created_order = await self.order_service.create_order(
                order_data=order_to_create,
                requesting_user_id=current_user.id
            )

            return f"Commande {created_order.id} créée avec succès ! Vous recevrez une confirmation par email."

        except (OrderCreationError, AddressNotFoundException):
            raise
        except Exception as e:
            logger.error(f"[ChatService] Erreur inattendue création commande user {current_user.id}: {e}", exc_info=True)
            raise OrderCreationError("Une erreur technique est survenue lors de la création de la commande", items_requested)

    # --- Méthodes utilitaires (potentiellement à déplacer/refactoriser) ---

    async def _generate_and_send_quote_pdf(self, quote_response, current_user: User, item_details: List[Dict[str, Any]]):
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

    async def _create_quote(self, current_user: User, quote_items_to_create: List[Dict[str, Any]]) -> Any:
        """
        Crée un devis avec les items spécifiés.
        
        Args:
            current_user: L'utilisateur pour qui créer le devis
            quote_items_to_create: Liste des items à inclure dans le devis
            
        Returns:
            Le devis créé
        """
        try:
            return await self.quote_service.create_quote(
                user_id=current_user.id,
                items=quote_items_to_create
            )
        except Exception as e:
            logger.error(f"[ChatService] Erreur création devis: {e}", exc_info=True)
            raise QuoteCreationError("Erreur lors de la création du devis", [])
