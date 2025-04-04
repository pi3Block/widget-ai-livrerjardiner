import logging
from typing import Optional, List, Annotated
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.concurrency import run_in_threadpool
import json
import random
from pydantic import BaseModel

# --- Importer la configuration --- 
import config

# --- Importer les modèles Pydantic V3 ---
import models # Imports User, UserCreate, Product, etc.

# --- Importer les fonctions CRUD V3 ---
import crud

# --- Importer logique LLM (sera adaptée plus tard) ---
from llm_logic import get_llm, stock_prompt, general_chat_prompt, parsing_prompt

# --- Importer le service d'envoi d'email (inchangé pour l'instant) ---
from services import send_quote_email

# --- Importer les utilitaires d'authentification ---
import auth # Imports create_access_token, get_current_active_user, Token

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LivrerJardiner API",
    description="API pour la gestion des produits, commandes, utilisateurs et interactions IA.",
    version="1.0.0" # Version V3 avec nouvelle structure
)

# Configurer CORS (inchangé)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://livrerjardiner.fr",
        "https://cdn.jsdelivr.net",
        "https://pierrelegrand.fr",
        "http://localhost:3000",
        "https://pi3block.github.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# Endpoints: Authentification & Utilisateurs
# ======================================================

@app.post("/auth/token", response_model=auth.Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """Fournit un token JWT pour un utilisateur authentifié."""
    logger.info(f"Tentative de login pour l'utilisateur: {form_data.username}")
    # authenticate_user attend email et password
    user = await run_in_threadpool(crud.authenticate_user, email=form_data.username, password=form_data.password)
    if not user:
        logger.warning(f"Échec de l'authentification pour: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Le "subject" du token est l'ID utilisateur
    access_token = auth.create_access_token(data={"sub": str(user.id)})
    logger.info(f"Token créé pour l'utilisateur: {form_data.username} (ID: {user.id})")
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=models.User, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: models.UserCreate):
    """Enregistre un nouvel utilisateur."""
    logger.info(f"Tentative d'enregistrement pour l'email: {user_in.email}")
    try:
        # La fonction CRUD gère déjà la vérification de l'email existant et le hashage
        created_user = await run_in_threadpool(crud.create_user, user=user_in)
        return created_user
    except HTTPException as e:
        # Remonter les erreurs spécifiques (ex: 409 Conflict si email existe)
        raise e 
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'enregistrement de l'utilisateur {user_in.email}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la création de l'utilisateur.")

@app.get("/users/me", response_model=models.User)
async def read_users_me(current_user: Annotated[models.User, Depends(auth.get_current_active_user)]):
    """Retourne les informations de l'utilisateur actuellement authentifié."""
    logger.info(f"Récupération des informations pour l'utilisateur ID: {current_user.id}")
    # La dépendance get_current_active_user a déjà récupéré et validé l'utilisateur
    # On pourrait vouloir rafraîchir les données ici si nécessaire (ex: re-récupérer les adresses)
    # user_data = crud.get_user_by_id(current_user.id) 
    # return user_data if user_data else current_user # Fallback au cas où
    return current_user

# ======================================================
# Endpoints: Adresses Utilisateur
# ======================================================

@app.post("/users/me/addresses", response_model=models.Address, status_code=status.HTTP_201_CREATED)
async def add_user_address(
    address_in: models.AddressCreate,
    current_user: Annotated[models.User, Depends(auth.get_current_active_user)]
):
    """Ajoute une nouvelle adresse pour l'utilisateur authentifié."""
    logger.info(f"Ajout d'adresse pour l'utilisateur ID: {current_user.id}")
    try:
        # crud.create_user_address gère la logique is_default
        created_address = await run_in_threadpool(crud.create_user_address, user_id=current_user.id, address=address_in)
        return created_address
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'ajout d'adresse pour user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de l'ajout de l'adresse.")

@app.get("/users/me/addresses", response_model=List[models.Address])
async def get_my_addresses(
    current_user: Annotated[models.User, Depends(auth.get_current_active_user)]
):
    """Liste les adresses de l'utilisateur authentifié."""
    logger.info(f"Listage des adresses pour l'utilisateur ID: {current_user.id}")
    try:
        addresses = await run_in_threadpool(crud.get_user_addresses, user_id=current_user.id)
        return addresses
    except Exception as e:
        logger.error(f"Erreur inattendue lors du listage des adresses pour user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la récupération des adresses.")

@app.put("/users/me/addresses/{address_id}/default", status_code=status.HTTP_204_NO_CONTENT)
async def set_my_default_address(
    address_id: int,
    current_user: Annotated[models.User, Depends(auth.get_current_active_user)]
):
    """Définit une adresse comme adresse par défaut pour l'utilisateur authentifié."""
    logger.info(f"Définition de l'adresse par défaut ID: {address_id} pour l'utilisateur ID: {current_user.id}")
    try:
        # crud.set_default_address gère la vérification d'appartenance et la transaction
        await run_in_threadpool(crud.set_default_address, user_id=current_user.id, address_id_to_set=address_id)
        return # Retourne 204 No Content en cas de succès
    except HTTPException as e:
        # Remonter les erreurs spécifiques (ex: 404 Not Found si l'adresse n'appartient pas à l'utilisateur)
        raise e
    except Exception as e:
        logger.error(f"Erreur lors de la définition de l'adresse par défaut {address_id} pour user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la mise à jour de l'adresse par défaut.")

# TODO: Endpoint PUT /users/me/addresses/{address_id} (utilise crud.update_user_address)
# @app.put("/users/me/addresses/{address_id}", response_model=models.Address)
# async def update_my_address(...):
#     pass

# TODO: Endpoint DELETE /users/me/addresses/{address_id} (utilise crud.delete_user_address)
# @app.delete("/users/me/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_my_address(...):
#     pass

# ======================================================
# Endpoints: Produits, Catégories, Tags
# ======================================================

# Ancien endpoint /products - Peut être supprimé plus tard
@app.get("/products_old", response_model=List[models.Product], deprecated=True)
async def list_products_old(limit: int = 100, offset: int = 0):
    """(Obsolète) Renvoie la liste des produits disponibles avec pagination."""
    logger.warning("Appel à l'endpoint obsolète /products_old")
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="Endpoint obsolète. Utiliser GET /products/")

# Nouvel endpoint /products
@app.get("/products/", response_model=List[models.Product])
async def list_products_v3(
    limit: int = 100, 
    offset: int = 0, 
    category_id: Optional[int] = None, 
    tags: Optional[str] = None, # Noms de tags séparés par des virgules
    search_term: Optional[str] = None
):
    """Renvoie la liste des produits avec variations, filtres et pagination."""
    logger.info(f"Requête list_products: limit={limit}, offset={offset}, category={category_id}, tags={tags}, search={search_term}")
    
    # Convertir la chaîne de tags en liste
    tag_names_list = tags.split(',') if tags else None
    if tag_names_list:
        tag_names_list = [tag.strip() for tag in tag_names_list if tag.strip()] # Nettoyer les espaces
        
    try:
        products = await run_in_threadpool(
            crud.list_products_with_variants, 
            limit=limit, 
            offset=offset, 
            category_id=category_id, 
            tag_names=tag_names_list, 
            search_term=search_term
        )
        return products
    except Exception as e:
        logger.error(f"Erreur lors du listage des produits: {e}", exc_info=True)
        # Utiliser un message d'erreur générique ou un des messages "amusants"
        error_message = random.choice(config.FUNNY_ERROR_MESSAGES) 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)

# TODO: Ajouter endpoints pour gérer Categories (POST, GET, PUT, DELETE) si nécessaire
# TODO: Ajouter endpoints pour gérer Tags (GET) si nécessaire
# TODO: Ajouter endpoints pour gérer Product Variants (POST, GET, PUT, DELETE) si nécessaire (pour admin)

# ======================================================
# Endpoints: Chat V3
# ======================================================

# Modèle pour la réponse du chat (simple pour l'instant)
class ChatResponse(BaseModel):
    message: str
    # On pourrait ajouter des champs pour guider le frontend:
    # next_action: Optional[str] = None # ex: 'request_address', 'confirm_order'
    # quote_id: Optional[int] = None
    # order_id: Optional[int] = None

@app.get("/chat", response_model=ChatResponse)
async def chat_v3(
    input: str,
    # delivery_method: str = "livraison", # Garder si utile pour le contexte LLM?
    current_user: Annotated[Optional[models.User], Depends(auth.get_current_user)] = None, # Optionnel
    selected_model: str = config.DEFAULT_MODEL
):
    """Point d'entrée principal pour les interactions via chat."""
    
    user_id_for_log = current_user.id if current_user else "Anonyme"
    logger.info(f"Requête chat V3 reçue : user={user_id_for_log}, model={selected_model}, input='{input}'")
    
    # Obtenir l'instance LLM
    current_llm = get_llm(selected_model)
    if not current_llm:
        logger.error(f"LLM demandé ({selected_model}) ou fallback non disponible")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=config.LLM_ERROR_MSG)

    # --- Étape 1 : Parsing de l'intention et des entités via LLM --- 
    parsed_data = None
    parsing_error = None
    try:
        logger.debug("Appel LLM (parsing V3)...")
        parsing_formatted_prompt = parsing_prompt.format(input=input)
        parsing_response_raw = await run_in_threadpool(current_llm.invoke, parsing_formatted_prompt)
        logger.debug(f"Réponse brute du parsing LLM: {parsing_response_raw}")

        # Nettoyer et parser la réponse JSON
        json_str = parsing_response_raw.strip().strip('```json').strip('```').strip()
        parsed_data = json.loads(json_str)
        logger.info(f"Parsing LLM réussi: {parsed_data}")
        
    except json.JSONDecodeError as e:
        parsing_error = f"Erreur de décodage JSON de la réponse du parsing LLM: {e}"
        logger.error(parsing_error)
    except Exception as e:
        parsing_error = f"Erreur inattendue lors du parsing LLM: {e}"
        logger.error(parsing_error, exc_info=True)
        
    # Si le parsing échoue, on traite comme info_generale
    if parsing_error or not parsed_data or "intent" not in parsed_data:
        logger.warning("Parsing LLM échoué ou invalide, traitement comme info_generale.")
        parsed_data = {"intent": "info_generale", "items": []}

    # --- Étape 2 : Traitement basé sur l'intention --- 
    intent = parsed_data.get("intent", "info_generale")
    items_requested = parsed_data.get("items", [])
    response_message = ""
    final_prompt = general_chat_prompt # Prompt par défaut
    prompt_input_vars = {"input": input}

    if intent == "info_generale" or intent == "salutation":
        # Simple réponse conversationnelle
        logger.debug(f"Intention traitée: {intent}")
        # Le prompt par défaut (general_chat_prompt) est déjà sélectionné
        pass 
        
    elif intent == "demande_produits":
        logger.debug(f"Intention traitée: {intent}")
        processed_items_info = []
        if not items_requested:
             # L'utilisateur a demandé des produits mais le LLM n'a rien extrait?
             logger.warning("Intention 'demande_produits' mais aucun item extrait.")
             response_message = "Je vois que vous cherchez des informations sur des produits, mais je n'ai pas bien compris lesquels. Pouvez-vous préciser les références (SKU) ou décrire les produits que vous cherchez ?"
             # Court-circuiter l'appel LLM final car on a déjà la réponse
             return ChatResponse(message=response_message)
        else:
            # Traiter chaque item demandé
            found_items_details = []
            not_found_skus = []
            stock_info_summary = "\nInformations sur les produits demandés:\n"
            
            for item in items_requested:
                sku = item.get("sku")
                quantity = item.get("quantity", 1)
                
                if sku:
                    logger.debug(f"Recherche variation SKU: {sku}")
                    variant = await run_in_threadpool(crud.get_product_variant_by_sku, sku=sku)
                    if variant:
                        logger.debug(f"Variation trouvée: {variant.id}, prix: {variant.price}")
                        stock_level = await run_in_threadpool(crud.get_stock_for_variant, variant_id=variant.id)
                        is_enough = stock_level >= quantity
                        found_items_details.append({ # Stocker les détails pour un prompt potentiel
                            "sku": sku, 
                            "stock": stock_level, 
                            "quantity": quantity, 
                            "is_enough": is_enough,
                            "price": variant.price
                        })
                        stock_info_summary += f"- Réf {sku}: Disponible: {stock_level} unité(s). (Prix: {variant.price:.2f} €)\n"
                    else:
                        logger.warning(f"SKU {sku} non trouvé dans la base de données.")
                        not_found_skus.append(sku)
                        stock_info_summary += f"- Réf {sku}: Désolé, cette référence est inconnue.\n"
                else:
                    # Cas où SKU non trouvé, mais base_product/attributes présents
                    # TODO: Implémenter la recherche par attributs si nécessaire
                    logger.warning(f"Item sans SKU détecté, recherche par attributs non implémentée: {item}")
                    stock_info_summary += f"- Pour '{item.get('base_product', 'produit inconnu')}', veuillez fournir la référence exacte (SKU) ou plus de détails.\n"

            # Préparer le contexte pour le prompt de réponse
            # Utiliser general_chat_prompt mais ajouter le résumé du stock
            prompt_input_vars["stock_summary"] = stock_info_summary
            final_prompt = PromptTemplate(
                input_variables=["input", "stock_summary"],
                template="L'utilisateur demande : {input}.\n{stock_summary}\nRéponds de manière utile et conviviale en te basant sur ces informations, en français uniquement."
            )
            # Note: On pourrait aussi utiliser stock_prompt si un seul item est demandé et pertinent.
            
    elif intent == "creer_devis":
        logger.debug(f"Intention traitée: {intent}")
        if not current_user:
             response_message = "Pour créer un devis, veuillez d'abord vous connecter ou créer un compte."
             return ChatResponse(message=response_message)
        if not items_requested:
             response_message = "Je peux créer un devis pour vous, mais veuillez d'abord spécifier les produits (avec leur référence SKU) et les quantités souhaitées."
             return ChatResponse(message=response_message)
        
        # TODO: Logique de création de devis (simplifié pour l'instant)
        # 1. Valider items (existence SKU, etc.)
        # 2. Préparer quote_in: models.QuoteCreate
        # 3. Appeler crud.create_quote
        # 4. Retourner confirmation
        response_message = f"Ok, je peux préparer un devis pour les articles demandés. (Fonctionnalité en cours de développement). Pour l'instant, voici les articles que j'ai compris: {items_requested}"
        return ChatResponse(message=response_message)

    elif intent == "passer_commande":
        logger.debug(f"Intention traitée: {intent}")
        if not current_user:
             response_message = "Pour passer commande, veuillez d'abord vous connecter ou créer un compte."
             return ChatResponse(message=response_message)
        if not items_requested:
             response_message = "Je peux vous aider à passer commande, mais veuillez d'abord spécifier les produits (avec leur référence SKU) et les quantités souhaitées."
             return ChatResponse(message=response_message)
        
        # TODO: Logique de création de commande (très simplifiée pour l'instant)
        # 1. Valider items (existence SKU, stock suffisant pour TOUS les items)
        # 2. Demander confirmation adresse livraison/facturation (nécessite dialogue ou lien frontend)
        # 3. Préparer order_in: models.OrderCreate
        # 4. Appeler crud.create_order
        # 5. Retourner confirmation
        response_message = f"Prêt à passer commande ! (Fonctionnalité en cours de développement). Je vérifierai le stock pour {items_requested}. Vous devrez ensuite confirmer vos adresses et le paiement sur la page de commande."
        return ChatResponse(message=response_message)

    else:
        # Intention inconnue, traiter comme info_generale
        logger.warning(f"Intention inconnue '{intent}', traitement comme info_generale.")
        # Le prompt par défaut (general_chat_prompt) est déjà sélectionné
        pass

    # --- Étape 3 : Génération de la réponse finale via LLM --- 
    try:
        logger.debug(f"Appel LLM (réponse finale) avec prompt: {final_prompt.template}")
        final_formatted_prompt = final_prompt.format(**prompt_input_vars)
        llm_response = await run_in_threadpool(current_llm.invoke, final_formatted_prompt)
        response_message = llm_response.strip()
        logger.info(f"Réponse finale LLM générée pour user={user_id_for_log}")
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la réponse finale LLM: {e}", exc_info=True)
        # Fallback vers un message générique
        response_message = "Désolé, je n'ai pas pu traiter complètement votre demande à cause d'une erreur interne." 
        # On pourrait utiliser un des FUNNY_ERROR_MESSAGES ici aussi

    return ChatResponse(message=response_message)

# ======================================================
# Endpoints: Devis (Quotes)
# ======================================================

@app.post("/quotes/", response_model=models.Quote, status_code=status.HTTP_201_CREATED)
async def create_new_quote(
    quote_in: models.QuoteCreate, # Le modèle QuoteCreate contient les items
    current_user: Annotated[models.User, Depends(auth.get_current_active_user)]
):
    """Crée un nouveau devis pour l'utilisateur authentifié."""
    logger.info(f"Création de devis pour l'utilisateur ID: {current_user.id}")
    # Assigner le user_id de l'utilisateur courant au devis
    # Note: Le modèle QuoteCreate n'a pas user_id, on le passe séparément à la fonction CRUD
    try:
        created_quote = await run_in_threadpool(crud.create_quote, user_id=current_user.id, quote_in=quote_in)
        # TODO: Potentiellement envoyer un email de notification ici
        return created_quote
    except HTTPException as e:
        raise e # Remonter les erreurs 404 (variation non trouvée) ou autres
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la création de devis pour user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la création du devis.")

@app.get("/quotes/", response_model=List[models.Quote])
async def get_my_quotes(
    current_user: Annotated[models.User, Depends(auth.get_current_active_user)],
    limit: int = 20, 
    offset: int = 0 
):
    """Liste les devis (en-têtes) de l'utilisateur authentifié."""
    logger.info(f"Listage des devis pour l'utilisateur ID: {current_user.id}")
    try:
        quotes = await run_in_threadpool(crud.list_user_quotes, user_id=current_user.id, limit=limit, offset=offset)
        return quotes
    except Exception as e:
        logger.error(f"Erreur inattendue lors du listage des devis pour user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la récupération des devis.")

@app.get("/quotes/{quote_id}", response_model=models.Quote)
async def get_specific_quote(
    quote_id: int,
    current_user: Annotated[models.User, Depends(auth.get_current_active_user)]
):
    """Récupère un devis spécifique de l'utilisateur authentifié."""
    logger.info(f"Récupération devis ID: {quote_id} pour utilisateur ID: {current_user.id}")
    try:
        quote = await run_in_threadpool(crud.get_quote_by_id, quote_id=quote_id)
        if not quote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Devis non trouvé.")
        # Vérifier que le devis appartient bien à l'utilisateur courant
        if quote.user_id != current_user.id:
            logger.warning(f"Tentative d'accès non autorisé au devis {quote_id} par l'utilisateur {current_user.id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à ce devis.")
        return quote
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la récupération du devis {quote_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la récupération du devis.")

# Modèle Pydantic pour la mise à jour du statut
class QuoteStatusUpdate(BaseModel):
    status: str

@app.put("/quotes/{quote_id}/status", response_model=models.Quote)
async def update_quote_status_endpoint(
    quote_id: int,
    status_update: QuoteStatusUpdate, # Utiliser le modèle Pydantic
    current_user: Annotated[models.User, Depends(auth.get_current_active_user)]
):
    """Met à jour le statut d'un devis de l'utilisateur authentifié."""
    logger.info(f"Mise à jour statut devis ID: {quote_id} -> {status_update.status} pour utilisateur ID: {current_user.id}")
    
    # Vérifier d'abord que le devis existe et appartient à l'utilisateur
    quote = await run_in_threadpool(crud.get_quote_by_id, quote_id=quote_id) # Récupère l'en-tête suffit
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Devis non trouvé.")
    if quote.user_id != current_user.id:
        logger.warning(f"Tentative de mise à jour non autorisée du statut du devis {quote_id} par l'utilisateur {current_user.id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à ce devis.")

    try:
        # Mettre à jour le statut via la fonction CRUD
        updated_quote = await run_in_threadpool(crud.update_quote_status, quote_id=quote_id, status=status_update.status)
        # La fonction CRUD update_quote_status retourne déjà le devis mis à jour ou lève une exception 404/400
        if not updated_quote: # Double sécurité
             raise HTTPException(status_code=500, detail="Erreur interne lors de la mise à jour du statut du devis.")
        # TODO: Si status == 'accepted', déclencher potentiellement la création de commande ?
        return updated_quote
    except HTTPException as e:
        raise e # Remonter 404, 400 (statut invalide)
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la mise à jour statut devis {quote_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la mise à jour du statut du devis.")

# ======================================================
# Endpoints: Commandes (Orders)
# ======================================================

@app.post("/orders/", response_model=models.Order, status_code=status.HTTP_201_CREATED)
async def create_new_order(
    order_in: models.OrderCreate, # Le modèle OrderCreate contient les items et infos de livraison
    current_user: Annotated[models.User, Depends(auth.get_current_active_user)]
):
    """Crée une nouvelle commande pour l'utilisateur authentifié."""
    logger.info(f"Création de commande pour l'utilisateur ID: {current_user.id}")
    # Assigner le user_id de l'utilisateur courant
    # Note: Le modèle OrderCreate n'a pas user_id dans sa définition de base, on le passe séparément à la fonction CRUD
    # Correction: OrderCreate hérite de OrderBase qui a user_id. Forçons-le qd même par sécurité.
    order_in_data = order_in.dict()
    order_in_data['user_id'] = current_user.id
    final_order_in = models.OrderCreate(**order_in_data) # Recrée l'objet avec le bon user_id
    
    try:
        # crud.create_order gère toute la logique transactionnelle:
        # vérification stock, création order + items, MAJ stock, création mouvements
        created_order = await run_in_threadpool(crud.create_order, user_id=current_user.id, order_in=final_order_in)
        # TODO: Envoyer un email de confirmation de commande ici
        return created_order
    except HTTPException as e:
        # Remonter les erreurs spécifiques (404 variation/user/adresse, 409 stock insuffisant, 400 montant...)
        raise e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la création de commande pour user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la création de la commande.")

@app.get("/orders/", response_model=List[models.Order])
async def get_my_orders(
    current_user: Annotated[models.User, Depends(auth.get_current_active_user)],
    limit: int = 20, 
    offset: int = 0
):
    """Liste les commandes (en-têtes) de l'utilisateur authentifié."""
    logger.info(f"Listage des commandes pour l'utilisateur ID: {current_user.id}")
    try:
        orders = await run_in_threadpool(crud.list_user_orders, user_id=current_user.id, limit=limit, offset=offset)
        return orders
    except Exception as e:
        logger.error(f"Erreur inattendue lors du listage des commandes pour user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la récupération des commandes.")

@app.get("/orders/{order_id}", response_model=models.Order)
async def get_specific_order(
    order_id: int,
    current_user: Annotated[models.User, Depends(auth.get_current_active_user)]
):
    """Récupère une commande spécifique de l'utilisateur authentifié."""
    logger.info(f"Récupération commande ID: {order_id} pour utilisateur ID: {current_user.id}")
    try:
        order = await run_in_threadpool(crud.get_order_by_id, order_id=order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée.")
        # Vérifier que la commande appartient bien à l'utilisateur courant
        if order.user_id != current_user.id:
            # TODO: Ajouter une logique de permission pour les admins plus tard
            logger.warning(f"Tentative d'accès non autorisé à la commande {order_id} par l'utilisateur {current_user.id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à cette commande.")
        return order
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la récupération de la commande {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la récupération de la commande.")

# Modèle Pydantic pour la mise à jour du statut de commande
class OrderStatusUpdate(BaseModel):
    status: str

@app.put("/orders/{order_id}/status", response_model=models.Order)
async def update_order_status_endpoint(
    order_id: int,
    status_update: OrderStatusUpdate,
    current_user: Annotated[models.User, Depends(auth.get_current_active_user)] # TODO: Devrait être un admin?
):
    """Met à jour le statut d'une commande (actuellement pour l'utilisateur propriétaire)."""
    logger.info(f"Mise à jour statut commande ID: {order_id} -> {status_update.status} par utilisateur ID: {current_user.id}")

    # Vérifier que la commande existe et appartient à l'utilisateur (ou est admin)
    # Utiliser get_order_by_id pour vérifier l'existence et l'appartenance en une fois
    order = await run_in_threadpool(crud.get_order_by_id, order_id=order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée.")
    if order.user_id != current_user.id:
        # TODO: Vérifier si current_user est admin
        logger.warning(f"Tentative de mise à jour non autorisée du statut de la commande {order_id} par l'utilisateur {current_user.id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à cette commande.")

    try:
        updated_order = await run_in_threadpool(crud.update_order_status, order_id=order_id, status=status_update.status)
        # La fonction crud retourne déjà l'objet mis à jour ou lève une exception
        if not updated_order: # Sécurité additionnelle
             raise HTTPException(status_code=500, detail="Erreur interne lors de la mise à jour du statut de la commande.")
        # TODO: Envoyer notification de changement de statut?
        return updated_order
    except HTTPException as e:
        raise e # Remonter 404, 400 (statut invalide)
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la mise à jour statut commande {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la mise à jour du statut de la commande.")

# Ancien endpoint /order - Sera supprimé plus tard
# @app.post("/order_old")
# async def create_order_old(order_data: models.OrderRequest): # Ancien modèle
#      logger.warning("Appel à l'ancien endpoint /order_old")
#      raise HTTPException(status_code=501, detail="Endpoint obsolète. Utiliser POST /orders/")

# Lancement (si exécuté directement, pour debug local)
# if __name__ == "__main__":
#     import uvicorn
#     logger.info("Démarrage du serveur Uvicorn pour le développement...")
#     uvicorn.run(app, host="0.0.0.0", port=8000)