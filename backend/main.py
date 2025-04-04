import logging
from typing import Optional, List, Annotated
from fastapi import FastAPI, HTTPException, Depends, status, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.concurrency import run_in_threadpool
import json
import random
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from jose import JWTError, jwt

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

# --- Importer la dépendance de session DB ---
from database import get_db_session, AsyncSession # Importer AsyncSession pour l'annotation

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LivrerJardiner API",
    description="API pour la gestion des produits, commandes, utilisateurs et interactions IA.",
    version="1.1.0" # Version avec SQLAlchemy + FastCRUD
)

# Configurer CORS (Mise à jour)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://livrerjardiner.fr",
        "https://cdn.jsdelivr.net",
        "https://pierrelegrand.fr",
        "http://localhost:3000",
        "https://pi3block.github.io",
        "http://localhost:5173", 
        "http://localhost",      
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range"],
)

# ======================================================
# Endpoints: Authentification & Utilisateurs
# ======================================================

@app.post("/auth/token", response_model=auth.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db_session) # Injecter la session DB
):
    """Fournit un token JWT pour un utilisateur authentifié."""
    logger.info(f"Tentative de login pour l'utilisateur: {form_data.username}")
    # Utiliser la nouvelle fonction crud.authenticate_user (async)
    # Elle retourne UserDB ou None
    user_db = await crud.authenticate_user(db=db, email=form_data.username, password=form_data.password)
    if not user_db:
        logger.warning(f"Échec de l'authentification pour: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Le subject du token est l'ID utilisateur
    access_token = auth.create_access_token(data={"sub": str(user_db.id)})
    logger.info(f"Token créé pour l'utilisateur: {form_data.username} (ID: {user_db.id})")
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=models.User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: models.UserCreate,
    db: AsyncSession = Depends(get_db_session) # Injecter la session DB
):
    """Enregistre un nouvel utilisateur."""
    logger.info(f"Tentative d'enregistrement pour l'email: {user_in.email}")
    try:
        # Utiliser la nouvelle fonction crud.create_user (async)
        created_user_db = await crud.create_user(db=db, user_in=user_in)
        # Mapper l'objet UserDB vers le schéma Pydantic User pour la réponse
        # Assure que models.User a Config.from_attributes = True
        return models.User.model_validate(created_user_db)
    except HTTPException as e:
        # Les erreurs spécifiques (ex: 409 Conflict) sont levées par crud.create_user
        raise e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'enregistrement de l'utilisateur {user_in.email}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la création de l'utilisateur.")

@app.get("/users/me", response_model=models.User)
async def read_users_me(
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)]
):
    """Retourne les informations de l'utilisateur actuellement authentifié."""
    logger.info(f"Récupération des informations pour l'utilisateur ID: {current_user_db.id}")
    # current_user_db contient déjà les infos et potentiellement les relations chargées
    # Mapper vers le modèle Pydantic pour la réponse
    return models.User.model_validate(current_user_db)

# ======================================================
# Endpoints: Adresses Utilisateur
# ======================================================

@app.post("/users/me/addresses", response_model=models.Address, status_code=status.HTTP_201_CREATED)
async def add_user_address(
    address_in: models.AddressCreate,
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    db: AsyncSession = Depends(get_db_session)
):
    """Ajoute une nouvelle adresse pour l'utilisateur authentifié."""
    logger.info(f"Ajout d'adresse pour l'utilisateur ID: {current_user_db.id}")
    try:
        created_address_db = await crud.create_user_address(db=db, user_id=current_user_db.id, address_in=address_in)
        return models.Address.model_validate(created_address_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'ajout d'adresse pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de l'ajout de l'adresse.")

@app.get("/users/me/addresses", response_model=List[models.Address])
async def get_my_addresses(
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    db: AsyncSession = Depends(get_db_session)
):
    """Liste les adresses de l'utilisateur authentifié."""
    logger.info(f"Listage des adresses pour l'utilisateur ID: {current_user_db.id}")
    try:
        addresses_db = await crud.get_user_addresses(db=db, user_id=current_user_db.id)
        return [models.Address.model_validate(addr) for addr in addresses_db]
    except Exception as e:
        logger.error(f"Erreur inattendue lors du listage des adresses pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la récupération des adresses.")

@app.put("/users/me/addresses/{address_id}/default", status_code=status.HTTP_204_NO_CONTENT)
async def set_my_default_address(
    address_id: int,
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    db: AsyncSession = Depends(get_db_session)
):
    """Définit une adresse comme adresse par défaut pour l'utilisateur authentifié."""
    logger.info(f"Définition de l'adresse par défaut ID: {address_id} pour l'utilisateur ID: {current_user_db.id}")
    try:
        await crud.set_default_address(db=db, user_id=current_user_db.id, address_id_to_set=address_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur lors de la définition de l'adresse par défaut {address_id} pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la mise à jour de l'adresse par défaut.")

@app.put("/users/me/addresses/{address_id}", response_model=models.Address)
async def update_my_address(
    address_id: int,
    address_in: models.AddressUpdate, # Utiliser le nouveau modèle Pydantic
    db: AsyncSession = Depends(get_db_session),
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)]
):
    """Met à jour une adresse spécifique de l'utilisateur authentifié."""
    logger.info(f"Tentative MAJ adresse ID {address_id} pour user ID {current_user_db.id}")
    updated_address_db = await crud.update_user_address(
        db=db, 
        user_id=current_user_db.id, 
        address_id=address_id, 
        address_in=address_in
    )
    if not updated_address_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Address with id {address_id} not found or does not belong to the current user."
        )
    # Mapper vers Pydantic pour la réponse
    return models.Address.model_validate(updated_address_db)

@app.delete("/users/me/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_address(
    address_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)]
):
    """Supprime une adresse spécifique de l'utilisateur authentifié."""
    logger.info(f"Tentative suppression adresse ID {address_id} pour user ID {current_user_db.id}")
    try:
        deleted = await crud.delete_user_address(db=db, user_id=current_user_db.id, address_id=address_id)
        # La fonction crud lève des exceptions 404 ou 400 si la suppression échoue/est invalide
        # Si elle retourne True, la suppression a réussi.
        # Pas de contenu à retourner (FastAPI gère le 204)
    except HTTPException as e:
        raise e # Remonter les erreurs 404 ou 400 de crud.delete_user_address
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la suppression de l'adresse {address_id} pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la suppression de l'adresse.")

# ======================================================
# Endpoints: Produits, Catégories, Tags
# ======================================================

# Endpoint pour lister les produits (avec filtres, pagination, Content-Range)
@app.get("/products", response_model=List[models.Product])
async def list_products(
    response: Response,
    limit: int = 100,
    offset: int = 0,
    category_id: Optional[int] = None,
    tags: Optional[str] = None, # Noms de tags séparés par des virgules
    search_term: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session) # Injecter la session DB
):
    """Renvoie la liste des produits avec variations, filtres et pagination."""
    logger.info(f"Requête list_products: limit={limit}, offset={offset}, category={category_id}, tags={tags}, search={search_term}")

    tag_names_list = tags.split(',') if tags else None
    if tag_names_list:
        tag_names_list = [tag.strip() for tag in tag_names_list if tag.strip()]

    try:
        # 1. Compter le total avec la nouvelle fonction
        total_count = await crud.count_products_with_variants(
            db=db,
            category_id=category_id,
            tag_names=tag_names_list,
            search_term=search_term
        )

        # 2. Obtenir les données paginées avec la nouvelle fonction
        products_db = await crud.list_products_with_variants(
            db=db,
            limit=limit,
            offset=offset,
            category_id=category_id,
            tag_names=tag_names_list,
            search_term=search_term
        )

        # 3. Construire et ajouter l'en-tête Content-Range
        end_range = offset + len(products_db) - 1 if len(products_db) > 0 else offset
        content_range_header = f"products {offset}-{end_range}/{total_count}"
        response.headers["Content-Range"] = content_range_header
        logger.debug(f"Setting Content-Range header: {content_range_header}")

        # 4. Mapper les ProductDB vers Product Pydantic pour la réponse
        return [models.Product.model_validate(p) for p in products_db]

    except Exception as e:
        logger.error(f"Erreur lors du listage des produits: {e}", exc_info=True)
        error_message = random.choice(config.FUNNY_ERROR_MESSAGES)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)

# Endpoint GET pour récupérer un produit spécifique par ID
@app.get("/products/{product_id}", response_model=models.Product)
async def read_product(
    product_id: int,
    db: AsyncSession = Depends(get_db_session) # Injecter la session DB
    # current_user: Annotated[models.User, Depends(auth.get_current_active_user)] # Décommenter si authentification requise
):
    """Récupère un produit spécifique par son ID, incluant ses variations."""
    logger.info(f"Requête get_product pour ID: {product_id}")
    try:
        # Utiliser la fonction refactorisée crud.get_product_by_id
        product_db = await crud.get_product_by_id(db=db, product_id=product_id)
        if product_db is None:
            logger.warning(f"Produit ID {product_id} non trouvé.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit non trouvé")
        # Mapper ProductDB vers Product Pydantic
        return models.Product.model_validate(product_db)
    except HTTPException as e:
        raise e # Remonter les erreurs HTTP (comme 404)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du produit ID {product_id}: {e}", exc_info=True)
        error_message = random.choice(config.FUNNY_ERROR_MESSAGES)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)

# Endpoint GET pour lister toutes les catégories
@app.get("/categories", response_model=List[models.Category])
async def list_all_categories(
    response: Response, # Gardé si on veut ajouter Content-Range plus tard
    db: AsyncSession = Depends(get_db_session) # Injecter la session DB
):
    """Renvoie la liste de toutes les catégories."""
    logger.info("Requête pour lister toutes les catégories")
    try:
        categories_db = await crud.get_all_categories(db=db)
        # Ajouter Content-Range (même si non paginé ici, peut être utile pour React Admin)
        total_count = len(categories_db)
        content_range_header = f"categories 0-{total_count-1 if total_count > 0 else 0}/{total_count}"
        response.headers["Content-Range"] = content_range_header
        logger.debug(f"Setting Content-Range header: {content_range_header}")
        # Mapper vers Pydantic
        return [models.Category.model_validate(cat) for cat in categories_db]
    except Exception as e:
        logger.error(f"Erreur lors du listage des catégories: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la récupération des catégories.")

# Endpoint GET pour récupérer une catégorie spécifique par ID
@app.get("/categories/{category_id}", response_model=models.Category)
async def read_category(
    category_id: int,
    db: AsyncSession = Depends(get_db_session) # Injecter la session DB
    # current_user: Annotated[models.User, Depends(auth.get_current_active_user)] # Décommenter si authentification requise
):
    """Récupère une catégorie spécifique par son ID."""
    logger.info(f"Requête get_category pour ID: {category_id}")
    try:
        # Utiliser la fonction crud.get_category refactorisée
        category_db = await crud.get_category(db=db, category_id=category_id)
        if category_db is None:
            logger.warning(f"Catégorie ID {category_id} non trouvée.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie non trouvée")
        # Mapper vers Pydantic
        return models.Category.model_validate(category_db)
    except HTTPException as e:
        raise e # Remonter les erreurs HTTP (comme 404)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la catégorie ID {category_id}: {e}", exc_info=True)
        error_message = random.choice(config.FUNNY_ERROR_MESSAGES)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)

# Endpoint POST pour créer un nouveau produit (Admin requis)
@app.post("/products", response_model=models.Product, status_code=status.HTTP_201_CREATED)
async def create_new_product(
    product_in: models.ProductCreate,
    db: AsyncSession = Depends(get_db_session),
    # Utiliser la dépendance admin
    current_admin_user: Annotated[models.UserDB, Depends(auth.get_current_admin_user)]
):
    """Crée un nouveau produit de base (Admin requis)."""
    logger.info(f"Tentative de création de produit par admin ID: {current_admin_user.id}")
    try:
        created_product_db = await crud.create_product(db=db, product_in=product_in)
        return models.Product.model_validate(created_product_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la création du produit '{product_in.name}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la création du produit.")

# Endpoint POST pour créer une nouvelle catégorie (Admin requis)
@app.post("/categories", response_model=models.Category, status_code=status.HTTP_201_CREATED)
async def create_new_category(
    category_in: models.CategoryCreate,
    db: AsyncSession = Depends(get_db_session),
    # Utiliser la dépendance admin
    current_admin_user: Annotated[models.UserDB, Depends(auth.get_current_admin_user)]
):
    """Crée une nouvelle catégorie (Admin requis)."""
    logger.info(f"Tentative de création de catégorie par admin ID: {current_admin_user.id}")
    try:
        created_category_db = await crud.create_category(db=db, category_in=category_in)
        return models.Category.model_validate(created_category_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la création de la catégorie '{category_in.name}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la création de la catégorie.")

# Endpoint POST pour créer une nouvelle variation pour un produit existant (Admin requis)
@app.post("/products/{product_id}/variants", response_model=models.ProductVariant, status_code=status.HTTP_201_CREATED)
async def create_product_variant_endpoint(
    product_id: int,
    variant_in: models.ProductVariantCreate,
    db: AsyncSession = Depends(get_db_session),
    # Utiliser la dépendance admin
    current_admin_user: Annotated[models.UserDB, Depends(auth.get_current_admin_user)]
):
    """Crée une nouvelle variation pour un produit existant (Admin requis)."""
    logger.info(f"Tentative création variation pour produit ID {product_id} par admin {current_admin_user.id}")
    if variant_in.product_id != product_id:
        logger.warning(f"Incohérence ID produit: URL={product_id}, Payload={variant_in.product_id}")
        variant_in.product_id = product_id

    try:
        created_variant_db = await crud.create_product_variant(db=db, variant_in=variant_in)
        return models.ProductVariant.model_validate(created_variant_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur création variation pour produit {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne création variation.")

# ======================================================
# Endpoints: Chat IA (Refactorisé)
# ======================================================

# Modèles Pydantic pour le Chat (inchangés)
class ChatRequest(BaseModel):
    input: str
    model: Optional[str] = config.DEFAULT_MODEL
    # Ajoutez d'autres champs si nécessaire (ex: user_id, session_id)

class ChatResponse(BaseModel):
    message: str
    # Ajoutez d'autres champs si nécessaire (ex: debug_info, detected_intent)

# --- Suppression des anciens endpoints spécifiques (/chat/stock, /chat/general, /chat/parse) --- 
# Ces logiques sont maintenant intégrées dans le endpoint /chat générique.

@app.post("/chat", response_model=ChatResponse) # Changer en POST pour accepter un corps de requête
async def chat_endpoint(
    request: ChatRequest, # Utiliser le modèle de requête
    db: AsyncSession = Depends(get_db_session), # Injecter la session DB
    # Utiliser la nouvelle dépendance pour l'utilisateur optionnel
    current_user_db: Annotated[Optional[models.UserDB], Depends(auth.get_optional_current_active_user)] = None
):
    """Point d'entrée principal pour les interactions via chat (refactorisé)."""
    
    user_id_for_log = current_user_db.id if current_user_db else "Anonyme"
    selected_model = request.model if request.model else config.DEFAULT_MODEL
    user_input = request.input
    
    logger.info(f"Requête chat reçue : user={user_id_for_log}, model={selected_model}, input='{user_input}'")
    
    # Obtenir l'instance LLM
    current_llm = get_llm(selected_model)
    if not current_llm:
        logger.error(f"LLM demandé ({selected_model}) ou fallback non disponible")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=config.LLM_ERROR_MSG)

    # --- Étape 1 : Parsing de l'intention et des entités via LLM --- 
    parsed_data = None
    parsing_error = None
    try:
        logger.debug("Appel LLM asynchrone (parsing)...")
        parsing_formatted_prompt = parsing_prompt.format(input=user_input)
        # Utiliser ainvoke pour l'appel asynchrone
        parsing_response_raw = await current_llm.ainvoke(parsing_formatted_prompt)
        logger.debug(f"Réponse brute du parsing LLM: {parsing_response_raw}")

        # Nettoyer et parser la réponse JSON (inchangé)
        json_str = parsing_response_raw.strip().strip('```json').strip('```').strip()
        parsed_data = json.loads(json_str)
        logger.info(f"Parsing LLM réussi: {parsed_data}")
        
    except json.JSONDecodeError as e:
        parsing_error = f"Erreur de décodage JSON de la réponse du parsing LLM: {e}"
        logger.error(parsing_error)
    except Exception as e:
        parsing_error = f"Erreur inattendue lors du parsing LLM: {e}"
        logger.error(parsing_error, exc_info=True)
        
    # Gestion de l'échec du parsing (inchangé)
    if parsing_error or not parsed_data or "intent" not in parsed_data:
        logger.warning("Parsing LLM échoué ou invalide, traitement comme info_generale.")
        parsed_data = {"intent": "info_generale", "items": []}

    # --- Étape 2 : Traitement basé sur l'intention --- 
    intent = parsed_data.get("intent", "info_generale")
    items_requested = parsed_data.get("items", [])
    response_message = ""
    final_prompt = general_chat_prompt # Prompt par défaut
    prompt_input_vars = {"input": user_input}
    should_call_llm = True # Par défaut, on appelle le LLM à la fin

    if intent == "info_generale" or intent == "salutation":
        logger.debug(f"Intention traitée: {intent}")
        pass # Utilise le prompt général
        
    elif intent == "demande_produits":
        logger.debug(f"Intention traitée: {intent}")
        if not items_requested:
             logger.warning("Intention 'demande_produits' mais aucun item extrait.")
             response_message = "Je vois que vous cherchez des informations sur des produits, mais je n'ai pas bien compris lesquels. Pouvez-vous préciser les références (SKU) ou décrire les produits que vous cherchez ?"
             should_call_llm = False # Pas besoin d'appeler le LLM, on a la réponse
        else:
            found_items_details = []
            not_found_skus = []
            stock_info_summary = "\nInformations sur les produits demandés:\n"
            for item in items_requested:
                sku = item.get("sku")
                quantity = item.get("quantity", 1)
                if sku:
                    variant = await crud.get_product_variant_by_sku(db=db, sku=sku)
                    if variant:
                        stock_info = await crud.get_stock_for_variant(db=db, variant_id=variant.id)
                        stock_level = stock_info.quantity if stock_info else 0
                        found_items_details.append({ 
                            "sku": sku, 
                            "stock": stock_level, 
                            "quantity": quantity, 
                            "is_enough": stock_level >= quantity,
                            "price": variant.price
                        })
                        stock_info_summary += f"- Réf {sku}: Disponible: {stock_level} unité(s). (Prix: {variant.price:.2f} €)\n"
                    else:
                        not_found_skus.append(sku)
                        stock_info_summary += f"- Réf {sku}: Désolé, cette référence est inconnue.\n"
                else:
                    stock_info_summary += f"- Pour '{item.get('base_product', 'produit inconnu')}', veuillez fournir la référence exacte (SKU).\n"
            
            prompt_input_vars["stock_summary"] = stock_info_summary
            final_prompt = PromptTemplate(
                input_variables=["input", "stock_summary"],
                template="L'utilisateur demande : {input}.\n{stock_summary}\nRéponds de manière utile et conviviale en te basant sur ces informations, en français uniquement."
            )
            # On laisse should_call_llm = True pour générer une réponse basée sur le résumé
            
    elif intent == "creer_devis":
        logger.debug(f"Intention traitée: {intent}")
        should_call_llm = False # On va générer une réponse directe

        if not current_user_db:
             response_message = "Pour créer un devis, veuillez d'abord vous connecter ou créer un compte."
        elif not items_requested:
             response_message = "Je peux créer un devis pour vous, mais veuillez d'abord spécifier les produits (avec leur référence SKU) et les quantités souhaitées."
        else:
            # Tenter de créer le devis
            quote_items_to_create: List[models.QuoteItemCreate] = []
            not_found_skus = []
            invalid_items = []
            try:
                for item in items_requested:
                    sku = item.get("sku")
                    quantity = item.get("quantity")
                    if not sku or not quantity or quantity <= 0:
                        invalid_items.append(item)
                        continue
                        
                    variant = await crud.get_product_variant_by_sku(db=db, sku=sku)
                    if not variant:
                        not_found_skus.append(sku)
                    else:
                        quote_items_to_create.append(
                            models.QuoteItemCreate(
                                product_variant_id=variant.id,
                                quantity=quantity,
                                price_at_quote=variant.price # Prix actuel pour le devis
                            )
                        )
                
                if invalid_items:
                    response_message = f"Certains articles demandés sont invalides (SKU ou quantité manquante/incorrecte): {invalid_items}. Veuillez corriger votre demande."
                elif not_found_skus:
                    response_message = f"Je n'ai pas pu trouver les produits avec les références suivantes: {', '.join(not_found_skus)}. Veuillez vérifier les références et réessayer."
                elif not quote_items_to_create:
                    response_message = "Je n'ai reconnu aucun produit valide pour créer un devis. Veuillez spécifier des produits avec référence (SKU) et quantité."
                else:
                    # Tous les items valides, créer le devis
                    quote_to_create = models.QuoteCreate(
                        user_id=current_user_db.id,
                        items=quote_items_to_create
                        # status et expires_at utilisent les valeurs par défaut du modèle
                    )
                    created_quote_db = await crud.create_quote(db=db, user_id=current_user_db.id, quote_in=quote_to_create)
                    response_message = f"Devis créé avec succès ! Votre numéro de devis est {created_quote_db.id}."
                    # TODO: Envoyer email? services.send_quote_email(...) 
            
            except HTTPException as e:
                 logger.error(f"HTTPException lors de la création du devis via chat pour user {current_user_db.id}: {e.detail}", exc_info=True)
                 response_message = f"Une erreur est survenue lors de la création du devis: {e.detail}"
            except Exception as e:
                 logger.error(f"Erreur inattendue lors de la création du devis via chat pour user {current_user_db.id}: {e}", exc_info=True)
                 response_message = "Désolé, une erreur interne m'empêche de créer le devis pour le moment."

    elif intent == "passer_commande":
        logger.debug(f"Intention traitée: {intent}")
        should_call_llm = False # Réponse directe

        if not current_user_db:
             response_message = "Pour passer commande, veuillez d'abord vous connecter ou créer un compte."
        elif not items_requested:
             response_message = "Je peux vous aider à passer commande, mais veuillez d'abord spécifier les produits (avec leur référence SKU) et les quantités souhaitées."
        else:
            default_address = await crud.get_default_address_for_user(db=db, user_id=current_user_db.id)
            if not default_address:
                response_message = "Vous n'avez pas d'adresse par défaut configurée. Veuillez en ajouter une via votre profil avant de passer commande."
            else:
                # Tenter de créer la commande
                order_items_to_create: List[models.OrderItemCreate] = []
                not_found_skus = []
                stock_issues = []
                invalid_items = []
                calculated_total = Decimal(0)
                try:
                    for item in items_requested:
                        sku = item.get("sku")
                        quantity = item.get("quantity")
                        if not sku or not quantity or quantity <= 0:
                            invalid_items.append(item)
                            continue
                            
                        variant = await crud.get_product_variant_by_sku(db=db, sku=sku)
                        if not variant:
                            not_found_skus.append(sku)
                            continue
                        
                        # Pré-vérification stock (la vraie vérif est dans crud.create_order)
                        stock_info = await crud.get_stock_for_variant(db=db, variant_id=variant.id)
                        current_stock = stock_info.quantity if stock_info else 0
                        if current_stock < quantity:
                            stock_issues.append(f"SKU {sku} (dispo: {current_stock}, demandé: {quantity})")
                            continue # Ne pas ajouter cet item
                        
                        price = variant.price
                        order_items_to_create.append(
                            models.OrderItemCreate(
                                product_variant_id=variant.id,
                                quantity=quantity,
                                price_at_order=price
                            )
                        )
                        calculated_total += (price * quantity)

                    if invalid_items:
                         response_message = f"Certains articles demandés sont invalides (SKU ou quantité manquante/incorrecte): {invalid_items}. Veuillez corriger votre demande."
                    elif not_found_skus:
                        response_message = f"Je n'ai pas pu trouver les produits avec les références suivantes: {', '.join(not_found_skus)}. Veuillez vérifier et réessayer."
                    elif stock_issues:
                        response_message = f"Stock insuffisant pour les articles suivants: {', '.join(stock_issues)}. Veuillez ajuster votre commande."
                    elif not order_items_to_create:
                         response_message = "Je n'ai reconnu aucun produit valide ou disponible pour passer commande. Veuillez spécifier des produits avec référence (SKU) et quantité."
                    else:
                        # Tout est OK pour tenter la création
                        order_to_create = models.OrderCreate(
                            user_id=current_user_db.id,
                            items=order_items_to_create,
                            delivery_address_id=default_address.id,
                            billing_address_id=default_address.id, # Simplification: utiliser la même
                            total_amount=calculated_total # Utiliser le total calculé
                            # status utilise la valeur par défaut
                        )
                        
                        # crud.create_order gère la transaction et les erreurs de stock finales
                        created_order_db = await crud.create_order(db=db, user_id=current_user_db.id, order_in=order_to_create)
                        response_message = f"Commande créée avec succès ! Votre numéro de commande est {created_order_db.id}. Elle sera expédiée à votre adresse par défaut."
                        # TODO: Envoyer email? services.send_order_confirmation_email(...) 
                
                except HTTPException as e:
                    # Capturer les erreurs spécifiques de crud.create_order (ex: 409 stock final)
                    logger.error(f"HTTPException lors de la création de la commande via chat pour user {current_user_db.id}: {e.detail}", exc_info=False) # Pas besoin de stacktrace complète pour 409 stock
                    response_message = f"Impossible de créer la commande: {e.detail}"
                except Exception as e:
                    logger.error(f"Erreur inattendue lors de la création de la commande via chat pour user {current_user_db.id}: {e}", exc_info=True)
                    response_message = "Désolé, une erreur interne m'empêche de passer la commande pour le moment."

    else:
        logger.warning(f"Intention inconnue '{intent}', traitement comme info_generale.")
        pass # Utilise le prompt général

    # --- Étape 3 : Génération de la réponse finale via LLM (si nécessaire) --- 
    if should_call_llm:
        try:
            logger.debug(f"Appel LLM asynchrone (réponse finale) avec prompt: {final_prompt.template}")
            final_formatted_prompt = final_prompt.format(**prompt_input_vars)
            llm_response = await current_llm.ainvoke(final_formatted_prompt)
            response_message = llm_response.strip()
            logger.info(f"Réponse finale LLM générée pour user={user_id_for_log}")
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la réponse finale LLM: {e}", exc_info=True)
            response_message = "Désolé, je n'ai pas pu traiter complètement votre demande à cause d'une erreur interne." 
    elif not response_message: # Fallback si should_call_llm est False mais response_message est vide
        logger.error("Erreur logique: should_call_llm est False mais aucun message de réponse directe n'a été défini.")
        response_message = "Désolé, je ne peux pas traiter votre demande pour le moment."

    return ChatResponse(message=response_message)

# ======================================================
# Endpoints: Devis (Quotes) (Vérifier propriété ou admin)
# Endpoints: Devis (Quotes)
# ======================================================

@app.post("/quotes", response_model=models.Quote, status_code=status.HTTP_201_CREATED)
async def create_new_quote(
    # Le payload doit correspondre à QuoteCreate (qui contient les QuoteItemCreate)
    quote_request: models.QuoteCreate, # Utiliser directement le modèle Pydantic
    db: AsyncSession = Depends(get_db_session),
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)]
):
    """Crée un nouveau devis pour l'utilisateur authentifié."""
    logger.info(f"Création devis pour user ID: {current_user_db.id}")
    # Assigner user_id de l'utilisateur connecté
    quote_request.user_id = current_user_db.id
    try:
        created_quote_db = await crud.create_quote(db=db, user_id=current_user_db.id, quote_in=quote_request)
        # Mapper vers Pydantic pour la réponse
        return models.Quote.model_validate(created_quote_db)
    except HTTPException as e:
        raise e # 404 si variation non trouvée
    except Exception as e:
        logger.error(f"Erreur création devis pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne création devis.")

@app.get("/quotes/{quote_id}", response_model=models.Quote)
async def read_quote(
    quote_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)]
):
    """Récupère un devis spécifique."""
    logger.info(f"Récupération devis ID: {quote_id} pour user {current_user_db.id}")
    try:
        quote_db = await crud.get_quote_by_id(db=db, quote_id=quote_id)
        if quote_db is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Devis non trouvé")
        # Vérifier que le devis appartient à l'utilisateur connecté
        if quote_db.user_id != current_user_db.id:
             logger.warning(f"Tentative d'accès non autorisé au devis {quote_id} par user {current_user_db.id}")
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à ce devis")
        # Mapper vers Pydantic
        return models.Quote.model_validate(quote_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur récupération devis {quote_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne récupération devis.")

@app.get("/users/me/quotes", response_model=List[models.Quote])
async def list_my_quotes(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)]
):
    """Liste les devis de l'utilisateur authentifié."""
    logger.info(f"Listage devis pour user {current_user_db.id}, limit={limit}, offset={offset}")
    try:
        quotes_db = await crud.list_user_quotes(db=db, user_id=current_user_db.id, limit=limit, offset=offset)
        # Mapper vers Pydantic
        return [models.Quote.model_validate(q) for q in quotes_db]
    except Exception as e:
        logger.error(f"Erreur listage devis pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne listage devis.")

# Endpoint pour mettre à jour le statut d'un devis
@app.patch("/quotes/{quote_id}/status", response_model=models.Quote)
async def update_quote_status_endpoint(
    quote_id: int,
    status_update: str = Body(..., embed=True, alias="status"),
    db: AsyncSession = Depends(get_db_session),
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)]
):
    """Met à jour le statut d'un devis."""
     # Vérifier que le devis appartient à l'utilisateur (ou admin)
    quote_db_check = await crud.get_quote_by_id(db=db, quote_id=quote_id)
    if not quote_db_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Devis non trouvé")
    if quote_db_check.user_id != current_user_db.id:
        # TODO: Ajouter vérification rôle admin si nécessaire
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à ce devis")

    logger.info(f"Mise à jour statut devis {quote_id} à '{status_update}' par user {current_user_db.id}")
    try:
        updated_quote_db = await crud.update_quote_status(db=db, quote_id=quote_id, status=status_update)
        # Mapper vers Pydantic
        return models.Quote.model_validate(updated_quote_db)
    except HTTPException as e:
        raise e # 400 (statut invalide), 404
    except Exception as e:
        logger.error(f"Erreur MAJ statut devis {quote_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne MAJ statut devis.")

# ======================================================
# Endpoints: Commandes (Orders)
# ======================================================

@app.post("/orders", response_model=models.Order, status_code=status.HTTP_201_CREATED)
async def create_new_order(
    order_request: models.OrderCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)]
):
    """Crée une nouvelle commande pour l'utilisateur authentifié."""
    logger.info(f"Création commande pour user ID: {current_user_db.id}")
    order_request.user_id = current_user_db.id
    try:
        created_order_db = await crud.create_order(db=db, user_id=current_user_db.id, order_in=order_request)
        # Mapper vers Pydantic
        return models.Order.model_validate(created_order_db)
    except HTTPException as e:
        raise e # 404 (user, adresse, variation), 409 (stock)
    except Exception as e:
        logger.error(f"Erreur création commande pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne création commande.")

@app.get("/orders/{order_id}", response_model=models.Order)
async def read_order(
    order_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)]
):
    """Récupère une commande spécifique."""
    logger.info(f"Récupération commande ID: {order_id} pour user {current_user_db.id}")
    try:
        order_db = await crud.get_order_by_id(db=db, order_id=order_id)
        if order_db is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée")
        if order_db.user_id != current_user_db.id:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à cette commande")
        # Mapper vers Pydantic
        return models.Order.model_validate(order_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur récupération commande {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne récupération commande.")

@app.get("/users/me/orders", response_model=List[models.Order])
async def list_my_orders(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)]
):
    """Liste les commandes de l'utilisateur authentifié."""
    logger.info(f"Listage commandes pour user {current_user_db.id}, limit={limit}, offset={offset}")
    try:
        orders_db = await crud.list_user_orders(db=db, user_id=current_user_db.id, limit=limit, offset=offset)
        # Mapper vers Pydantic
        return [models.Order.model_validate(o) for o in orders_db]
    except Exception as e:
        logger.error(f"Erreur listage commandes pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne listage commandes.")

# Endpoint pour mettre à jour le statut d'une commande
@app.patch("/orders/{order_id}/status", response_model=models.Order)
async def update_order_status_endpoint(
    order_id: int,
    status_update: str = Body(..., embed=True, alias="status"),
    db: AsyncSession = Depends(get_db_session),
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)]
):
    """Met à jour le statut d'une commande."""
    # Vérifier appartenance (ou rôle admin)
    order_db_check = await crud.get_order_by_id(db=db, order_id=order_id)
    if not order_db_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée")
    if order_db_check.user_id != current_user_db.id:
        # TODO: Vérifier si admin
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à cette commande")

    logger.info(f"Mise à jour statut commande {order_id} à '{status_update}' par user {current_user_db.id}")
    try:
        updated_order_db = await crud.update_order_status(db=db, order_id=order_id, status=status_update)
        # Mapper vers Pydantic
        return models.Order.model_validate(updated_order_db)
    except HTTPException as e:
        raise e # 400, 404
    except Exception as e:
        logger.error(f"Erreur MAJ statut commande {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne MAJ statut commande.")

# ======================================================
# Initialisation & Lancement (Non modifié)
# ======================================================
# ... (si vous avez une fonction main ou similaire) ...

# Note: L'ancien endpoint /products_old a été supprimé car marqué deprecated et levait une erreur.

# Lancement (si exécuté directement, pour debug local)
# if __name__ == "__main__":
#     import uvicorn
#     logger.info("Démarrage du serveur Uvicorn pour le développement...")
#     uvicorn.run(app, host="0.0.0.0", port=8000)