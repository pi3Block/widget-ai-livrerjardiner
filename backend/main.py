import logging
from typing import Optional, List, Annotated, Any, Dict, Tuple
from fastapi import FastAPI, HTTPException, Depends, status, Response, Body, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.concurrency import run_in_threadpool
import json
import random
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from jose import JWTError, jwt
from decimal import Decimal # Ajout pour passer_commande

# --- Importer la configuration --- 
import config

# --- Importer les modèles SQLAlchemy DB --- 
import models # Contient maintenant uniquement les modèles DB (ex: UserDB, AddressDB)

# --- Importer les Schémas Pydantic --- 
import schemas # Nouveau fichier contenant les schémas Pydantic (ex: User, UserCreate)

# --- Importer les fonctions CRUD V3 ---
import crud

# --- Importer logique LLM (sera adaptée plus tard) ---
from llm_logic import get_llm, stock_prompt, general_chat_prompt, parsing_prompt

# --- Importer le service d'envoi d'email (inchangé pour l'instant) ---
import services # Importer le module complet
import pdf_utils # Ajout pour la génération PDF

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
        "http://localhost:4000",      
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
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Tentative de login pour l'utilisateur: {form_data.username}")
    # Utiliser la fonction crud.authenticate_user (retourne un dict ou None)
    user_dict = await crud.authenticate_user(db=db, email=form_data.username, password=form_data.password)
    if not user_dict:
        logger.warning(f"Échec de l'authentification pour: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": str(user_dict['id'])})
    logger.info(f"Token créé pour l'utilisateur: {form_data.username} (ID: {user_dict['id']})")
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=schemas.UserBase, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: schemas.UserCreate,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Tentative d'enregistrement pour l'email: {user_in.email}")
    try:
        created_user_db = await crud.create_user(db=db, user_in=user_in)
        # Mapper l'objet UserDB vers le schéma Pydantic UserBase pour la réponse
        return schemas.UserBase.model_validate(created_user_db)
    except HTTPException as e:
        raise e 
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'enregistrement de l'utilisateur {user_in.email}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la création de l'utilisateur.")

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)]
):
    logger.info(f"Récupération des informations pour l'utilisateur ID: {current_user_db.id}")
    # Essayer la validation Pydantic directement
    return schemas.User.model_validate(current_user_db)

# ======================================================
# Endpoints: Adresses Utilisateur
# ======================================================

@app.post("/users/me/addresses", response_model=schemas.Address, status_code=status.HTTP_201_CREATED)
async def add_user_address(
    address_in: schemas.AddressCreate,
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Ajout d'adresse pour l'utilisateur ID: {current_user_db.id}")
    try:
        created_address_db = await crud.create_user_address(db=db, user_id=current_user_db.id, address_in=address_in)
        return schemas.Address.model_validate(created_address_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'ajout d'adresse pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de l'ajout de l'adresse.")

@app.get("/users/me/addresses", response_model=List[schemas.Address])
async def get_my_addresses(
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Listage des adresses pour l'utilisateur ID: {current_user_db.id}")
    try:
        addresses_db = await crud.get_user_addresses(db=db, user_id=current_user_db.id)
        return [schemas.Address.model_validate(addr) for addr in addresses_db]
    except Exception as e:
        logger.error(f"Erreur inattendue lors du listage des adresses pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la récupération des adresses.")

@app.put("/users/me/addresses/{address_id}/default", status_code=status.HTTP_204_NO_CONTENT)
async def set_my_default_address(
    address_id: int,
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Définition de l'adresse par défaut ID: {address_id} pour l'utilisateur ID: {current_user_db.id}")
    try:
        await crud.set_default_address(db=db, user_id=current_user_db.id, address_id_to_set=address_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur lors de la définition de l'adresse par défaut {address_id} pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la mise à jour de l'adresse par défaut.")

@app.put("/users/me/addresses/{address_id}", response_model=schemas.Address)
async def update_my_address(
    address_id: int,
    address_in: schemas.AddressUpdate,
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    db: AsyncSession = Depends(get_db_session)
):
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
    return schemas.Address.model_validate(updated_address_db)

@app.delete("/users/me/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_address(
    address_id: int,
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Tentative suppression adresse ID {address_id} pour user ID {current_user_db.id}")
    try:
        deleted = await crud.delete_user_address(db=db, user_id=current_user_db.id, address_id=address_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la suppression de l'adresse {address_id} pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la suppression de l'adresse.")

# ======================================================
# Endpoints: Produits, Catégories, Tags
# ======================================================

@app.get("/products", response_model=List[schemas.Product])
async def list_products(
    response: Response,
    limit: int = 100, 
    offset: int = 0, 
    category_id: Optional[int] = None, 
    tags: Optional[str] = None,
    search_term: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Requête list_products: limit={limit}, offset={offset}, category={category_id}, tags={tags}, search={search_term}")
    tag_names_list = tags.split(',') if tags else None
    if tag_names_list:
        tag_names_list = [tag.strip() for tag in tag_names_list if tag.strip()]
        
    try:
        total_count = await crud.count_products_with_variants(
            db=db,
            category_id=category_id, 
            tag_names=tag_names_list, 
            search_term=search_term
        )
        products_db = await crud.list_products_with_variants(
            db=db,
            limit=limit, 
            offset=offset, 
            category_id=category_id, 
            tag_names=tag_names_list, 
            search_term=search_term
        )
        end_range = offset + len(products_db) - 1 if len(products_db) > 0 else offset
        content_range_header = f"products {offset}-{end_range}/{total_count}"
        response.headers["Content-Range"] = content_range_header
        logger.debug(f"Setting Content-Range header: {content_range_header}")
        return [schemas.Product.model_validate(p) for p in products_db]
    except Exception as e:
        logger.error(f"Erreur lors du listage des produits: {e}", exc_info=True)
        error_message = random.choice(config.FUNNY_ERROR_MESSAGES) 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)

@app.get("/products/{product_id}", response_model=schemas.Product)
async def read_product(
    product_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Requête get_product pour ID: {product_id}")
    try:
        product_db = await crud.get_product_by_id(db=db, product_id=product_id)
        if product_db is None:
            logger.warning(f"Produit ID {product_id} non trouvé.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit non trouvé")
        return schemas.Product.model_validate(product_db)
    except HTTPException as e:
        raise e 
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du produit ID {product_id}: {e}", exc_info=True)
        error_message = random.choice(config.FUNNY_ERROR_MESSAGES)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)

# Helper pour parser les paramètres React-Admin
def parse_react_admin_params(
    request: Request,
    filter: Optional[str] = Query(None), # Encodé en JSON
    range: Optional[str] = Query(None),  # Encodé en JSON -> [start, end]
    sort: Optional[str] = Query(None)    # Encodé en JSON -> [field, order]
) -> Tuple[int, int, Optional[str], bool, Optional[Dict[str, Any]]]:
    """Parse les query params de React-Admin et retourne limit, offset, sort_by, sort_desc, filters."""
    offset = 0
    limit = 100 # Default limit
    sort_by = None
    sort_desc = False
    filters = None

    if range:
        try:
            range_list = json.loads(range)
            if isinstance(range_list, list) and len(range_list) == 2:
                offset = int(range_list[0])
                limit = int(range_list[1]) - offset + 1
        except (json.JSONDecodeError, ValueError, IndexError):
            logger.warning(f"Paramètre 'range' invalide: {range}. Utilisation défauts.")

    if sort:
        try:
            sort_list = json.loads(sort)
            if isinstance(sort_list, list) and len(sort_list) == 2:
                sort_by = str(sort_list[0])
                sort_desc = str(sort_list[1]).upper() == 'DESC'
        except (json.JSONDecodeError, ValueError, IndexError):
            logger.warning(f"Paramètre 'sort' invalide: {sort}. Pas de tri appliqué.")

    if filter:
        try:
            filters = json.loads(filter)
            if not isinstance(filters, dict):
                 logger.warning(f"Paramètre 'filter' n'est pas un dict valide: {filter}. Pas de filtres appliqués.")
                 filters = None
            # TODO: Potentiellement, adapter les noms de champs si nécessaire entre frontend et DB
        except json.JSONDecodeError:
            logger.warning(f"Paramètre 'filter' n'est pas du JSON valide: {filter}. Pas de filtres appliqués.")
            filters = None
    
    return limit, offset, sort_by, sort_desc, filters

# NOUVEL endpoint /categories pour React-Admin
@app.get("/categories", response_model=List[schemas.Category])
async def list_categories_endpoint(
    response: Response,
    # Utilisation d'une dépendance pour parser les params
    params: Tuple[int, int, Optional[str], bool, Optional[Dict[str, Any]]] = Depends(parse_react_admin_params),
    db: AsyncSession = Depends(get_db_session)
):
    limit, offset, sort_by, sort_desc, filters = params
    logger.info(f"Requête list_categories: limit={limit}, offset={offset}, sort={sort_by}, desc={sort_desc}, filters={filters}")
    
    try:
        categories_db_list, total_count = await crud.list_categories(
            db=db,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc,
            filters=filters
        )
        
        # Calculer l'index de fin pour Content-Range
        end_range = offset + len(categories_db_list) - 1 if len(categories_db_list) > 0 else offset
        content_range_header = f"categories {offset}-{end_range}/{total_count}"
        response.headers["Content-Range"] = content_range_header
        logger.debug(f"Setting Content-Range header: {content_range_header}")
        
        # Convertir les modèles DB en schémas Pydantic pour la réponse
        return [schemas.Category.model_validate(cat_db) for cat_db in categories_db_list]
        
    except Exception as e:
        logger.error(f"Erreur lors du listage des catégories: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la récupération des catégories.")

@app.get("/categories/{category_id}", response_model=schemas.Category)
async def read_category(
    category_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Requête get_category pour ID: {category_id}")
    try:
        # crud.get_category retourne Optional[models.CategoryDB]
        category_db = await crud.get_category(db=db, category_id=category_id)
        if category_db is None:
            logger.warning(f"Catégorie ID {category_id} non trouvée.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie non trouvée")
        return schemas.Category.model_validate(category_db)
    except HTTPException as e:
        raise e 
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la catégorie ID {category_id}: {e}", exc_info=True)
        error_message = random.choice(config.FUNNY_ERROR_MESSAGES)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)

@app.post("/products", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
async def create_new_product(
    product_in: schemas.ProductCreate,
    current_admin_user: Annotated[models.UserDB, Depends(auth.get_current_admin_user)],
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Tentative de création de produit par admin ID: {current_admin_user.id}")
    try:
        created_product_db = await crud.create_product(db=db, product_in=product_in)
        return schemas.Product.model_validate(created_product_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la création du produit '{product_in.name}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la création du produit.")

@app.post("/categories", response_model=schemas.Category, status_code=status.HTTP_201_CREATED)
async def create_new_category(
    category_in: schemas.CategoryCreate,
    current_admin_user: Annotated[models.UserDB, Depends(auth.get_current_admin_user)],
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Tentative de création de catégorie par admin ID: {current_admin_user.id}")
    try:
        created_category_db = await crud.create_category(db=db, category_in=category_in)
        return schemas.Category.model_validate(created_category_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la création de la catégorie '{category_in.name}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors de la création de la catégorie.")

@app.post("/products/{product_id}/variants", response_model=schemas.ProductVariant, status_code=status.HTTP_201_CREATED)
async def create_product_variant_endpoint(
    product_id: int,
    variant_in: schemas.ProductVariantCreate,
    current_admin_user: Annotated[models.UserDB, Depends(auth.get_current_admin_user)],
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Tentative création variation pour produit ID {product_id} par admin {current_admin_user.id}")
    if variant_in.product_id != product_id:
        logger.warning(f"Incohérence ID produit: URL={product_id}, Payload={variant_in.product_id}")
        variant_in.product_id = product_id

    try:
        created_variant_db = await crud.create_product_variant(db=db, variant_in=variant_in)
        return schemas.ProductVariant.model_validate(created_variant_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur création variation pour produit {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne création variation.")

# ======================================================
# Endpoints: Chat IA (Refactorisé)
# ======================================================

class ChatRequest(BaseModel):
    input: str
    model: Optional[str] = config.DEFAULT_MODEL

class ChatResponse(BaseModel):
    message: str

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user_db: Annotated[Optional[models.UserDB], Depends(auth.get_optional_current_active_user)] = None
):
    user_id_for_log = current_user_db.id if current_user_db else "Anonyme"
    selected_model = request.model if request.model else config.DEFAULT_MODEL
    user_input = request.input
    logger.info(f"Requête chat reçue : user={user_id_for_log}, model={selected_model}, input='{user_input}'")
    
    current_llm = get_llm(selected_model)
    if not current_llm:
        logger.error(f"LLM demandé ({selected_model}) ou fallback non disponible")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=config.LLM_ERROR_MSG)

    # --- Étape 1 : Parsing --- 
    parsed_data = None
    parsing_error = None
    try:
        logger.debug("Appel LLM asynchrone (parsing)...")
        parsing_formatted_prompt = parsing_prompt.format(input=user_input)
        parsing_response_raw = await current_llm.ainvoke(parsing_formatted_prompt)
        logger.debug(f"Réponse brute du parsing LLM: {parsing_response_raw}")
        json_str = parsing_response_raw.strip().strip('```json').strip('```').strip()
        parsed_data = json.loads(json_str)
        logger.info(f"Parsing LLM réussi: {parsed_data}")
    except json.JSONDecodeError as e:
        parsing_error = f"Erreur de décodage JSON du parsing LLM: {e}"
        logger.error(parsing_error)
    except Exception as e:
        parsing_error = f"Erreur inattendue lors du parsing LLM: {e}"
        logger.error(parsing_error, exc_info=True)
        
    if parsing_error or not parsed_data or "intent" not in parsed_data:
        logger.warning("Parsing LLM échoué ou invalide, traitement comme info_generale.")
        parsed_data = {"intent": "info_generale", "items": []}

    # --- Étape 2 : Traitement basé sur l'intention --- 
    intent = parsed_data.get("intent", "info_generale")
    items_requested = parsed_data.get("items", [])
    response_message = ""
    final_prompt = general_chat_prompt
    prompt_input_vars = {"input": user_input}
    should_call_llm = True

    if intent == "info_generale" or intent == "salutation":
        logger.debug(f"Intention traitée: {intent}")
        pass
    elif intent == "demande_produits":
        logger.debug(f"Intention traitée: {intent}")
        if not items_requested:
             logger.warning("Intention 'demande_produits' mais aucun item extrait.")
             response_message = "Je vois que vous cherchez des informations sur des produits, mais je n'ai pas bien compris lesquels. Pouvez-vous préciser les références (SKU) ou décrire les produits que vous cherchez ?"
             should_call_llm = False
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
                            "sku": sku, "stock": stock_level, "quantity": quantity, 
                            "is_enough": stock_level >= quantity, "price": variant.price
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
    elif intent == "creer_devis":
        logger.debug(f"Intention traitée: {intent}")
        should_call_llm = False
        if not current_user_db:
             response_message = "Pour créer un devis, veuillez d'abord vous connecter ou créer un compte."
        elif not items_requested:
             response_message = "Je peux créer un devis pour vous, mais veuillez d'abord spécifier les produits (avec leur référence SKU) et les quantités souhaitées."
        else:
            quote_items_to_create: List[schemas.QuoteItemCreate] = []
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
                            schemas.QuoteItemCreate(
                                product_variant_id=variant.id,
                                quantity=quantity,
                                unit_price=variant.price
                            )
                        )
                if invalid_items:
                    response_message = f"Certains articles demandés sont invalides: {invalid_items}."
                elif not_found_skus:
                    response_message = f"Produits non trouvés: {', '.join(not_found_skus)}."
                elif not quote_items_to_create:
                    response_message = "Aucun produit valide reconnu."
                else:
                    quote_to_create = schemas.QuoteCreate(
                        user_id=current_user_db.id,
                        items=quote_items_to_create
                    )
                    created_quote_db = await crud.create_quote(db=db, user_id=current_user_db.id, quote_in=quote_to_create)
                    response_message = f"Devis créé avec succès ! Votre numéro de devis est {created_quote_db.id}."
                    try:
                        full_quote_db = await crud.get_quote_by_id(db, created_quote_db.id)
                        if not full_quote_db:
                            logger.error(f"[CHAT] Erreur fetch devis {created_quote_db.id} après création.")
                        else:
                            pdf_path = pdf_utils.generate_quote_pdf(full_quote_db)
                            logger.info(f"[CHAT] PDF devis {created_quote_db.id} généré: {pdf_path}")
                            await services.send_quote_email(
                                user_email=current_user_db.email, 
                                quote_id=created_quote_db.id, 
                                pdf_path=pdf_path
                            )
                            logger.info(f"Appel send_quote_email effectué pour devis {created_quote_db.id} depuis Chat.")
                    except Exception as email_error:
                        logger.error(f"Erreur envoi email devis {created_quote_db.id} depuis Chat: {email_error}", exc_info=True)
            except HTTPException as e:
                 logger.error(f"HTTPException création devis via chat user {current_user_db.id}: {e.detail}", exc_info=True)
                 response_message = f"Erreur création devis: {e.detail}"
            except Exception as e:
                 logger.error(f"Erreur inattendue création devis via chat user {current_user_db.id}: {e}", exc_info=True)
                 response_message = "Erreur interne création devis."
    elif intent == "passer_commande":
        logger.debug(f"Intention traitée: {intent}")
        should_call_llm = False
        if not current_user_db:
             response_message = "Pour passer commande, veuillez d'abord vous connecter ou créer un compte."
        elif not items_requested:
             response_message = "Je peux vous aider à passer commande, mais veuillez d'abord spécifier les produits (avec leur référence SKU) et les quantités souhaitées."
        else:
            default_address = await crud.get_default_address_for_user(db=db, user_id=current_user_db.id)
            if not default_address:
                response_message = "Veuillez configurer une adresse par défaut avant de passer commande."
            else:
                order_items_to_create: List[schemas.OrderItemCreate] = []
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
                        stock_info = await crud.get_stock_for_variant(db=db, variant_id=variant.id)
                        current_stock = stock_info.quantity if stock_info else 0
                        if current_stock < quantity:
                            stock_issues.append(f"SKU {sku} (dispo: {current_stock}, demandé: {quantity})")
                            continue
                        price = variant.price
                        order_items_to_create.append(
                            schemas.OrderItemCreate(
                                product_variant_id=variant.id,
                                quantity=quantity,
                                unit_price=price
                            )
                        )
                        calculated_total += (price * quantity)
                    if invalid_items:
                         response_message = f"Articles invalides: {invalid_items}."
                    elif not_found_skus:
                        response_message = f"Produits non trouvés: {', '.join(not_found_skus)}."
                    elif stock_issues:
                        response_message = f"Stock insuffisant: {', '.join(stock_issues)}."
                    elif not order_items_to_create:
                         response_message = "Aucun produit valide ou disponible reconnu."
                    else:
                        order_to_create = schemas.OrderCreate(
                            user_id=current_user_db.id,
                            items=order_items_to_create,
                            delivery_address_id=default_address.id,
                            billing_address_id=default_address.id,
                            total_price=calculated_total
                        )
                        created_order_db = await crud.create_order(db=db, user_id=current_user_db.id, order_in=order_to_create)
                        response_message = f"Commande créée avec succès ! Numéro: {created_order_db.id}."
                        try:
                            logger.info(f"Tentative envoi email confirmation commande {created_order_db.id} à {current_user_db.email} depuis Chat.")
                            await services.send_order_confirmation_email(
                                user_email=current_user_db.email, 
                                order=created_order_db
                            )
                            logger.info(f"Appel send_order_confirmation_email effectué pour commande {created_order_db.id} depuis Chat.")
                        except Exception as email_error:
                            logger.error(f"Erreur envoi email commande {created_order_db.id} depuis Chat: {email_error}", exc_info=True)
                except HTTPException as e:
                    logger.error(f"HTTPException création commande via chat user {current_user_db.id}: {e.detail}", exc_info=False)
                    response_message = f"Impossible de créer la commande: {e.detail}"
                except Exception as e:
                    logger.error(f"Erreur inattendue création commande via chat user {current_user_db.id}: {e}", exc_info=True)
                    response_message = "Erreur interne création commande."
    else:
        logger.warning(f"Intention inconnue '{intent}', traitement comme info_generale.")
        pass

    # --- Étape 3 : Génération réponse finale --- 
    if should_call_llm:
        try:
            logger.debug(f"Appel LLM final avec prompt: {final_prompt.template}")
            final_formatted_prompt = final_prompt.format(**prompt_input_vars)
            llm_response = await current_llm.ainvoke(final_formatted_prompt)
            response_message = llm_response.strip()
            logger.info(f"Réponse finale LLM générée pour user={user_id_for_log}")
        except Exception as e:
            logger.error(f"Erreur génération réponse finale LLM: {e}", exc_info=True)
            response_message = "Désolé, erreur interne lors de la génération de la réponse."
    elif not response_message:
        logger.error("Erreur logique: should_call_llm=False mais response_message vide.")
        response_message = "Désolé, erreur interne."

    return ChatResponse(message=response_message)

# ======================================================
# Endpoints: Devis (Quotes)
# ======================================================

@app.post("/quotes", response_model=schemas.Quote, status_code=status.HTTP_201_CREATED)
async def create_new_quote(
    quote_request: schemas.QuoteCreate,
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Création devis pour user ID: {current_user_db.id}")
    if quote_request.user_id != current_user_db.id:
        logger.warning(f"Incohérence user ID création devis (token: {current_user_db.id}, payload: {quote_request.user_id}). Utilisation ID token.")
        quote_request.user_id = current_user_db.id 
    try:
        created_quote_db = await crud.create_quote(db=db, user_id=current_user_db.id, quote_in=quote_request)
        try:
            full_quote_db = await crud.get_quote_by_id(db, created_quote_db.id)
            if not full_quote_db:
                logger.error(f"[POST /quotes] Erreur fetch devis {created_quote_db.id} après création.")
            else:
                pdf_path = pdf_utils.generate_quote_pdf(full_quote_db)
                logger.info(f"[POST /quotes] PDF devis {created_quote_db.id} généré: {pdf_path}")
                await services.send_quote_email(
                    user_email=current_user_db.email, 
                    quote_id=created_quote_db.id, 
                    pdf_path=pdf_path
                )
                logger.info(f"Appel send_quote_email effectué pour devis {created_quote_db.id} depuis POST /quotes.")
        except Exception as email_error:
            logger.error(f"Erreur envoi email devis {created_quote_db.id} (depuis POST /quotes): {email_error}", exc_info=True)
        return schemas.Quote.model_validate(created_quote_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur création devis pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne création devis.")

@app.get("/quotes/{quote_id}", response_model=schemas.Quote)
async def read_quote(
    quote_id: int,
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Récupération devis ID: {quote_id} pour user {current_user_db.id}")
    try:
        quote_db = await crud.get_quote_by_id(db=db, quote_id=quote_id)
        if quote_db is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Devis non trouvé")
        if quote_db.user_id != current_user_db.id:
             logger.warning(f"Accès non autorisé devis {quote_id} par user {current_user_db.id}")
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à ce devis")
        return schemas.Quote.model_validate(quote_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur récupération devis {quote_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne récupération devis.")

@app.get("/users/me/quotes", response_model=List[schemas.Quote])
async def list_my_quotes(
    limit: int = 20,
    offset: int = 0,
    current_user_db: models.UserDB = Depends(auth.get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Listage devis pour user {current_user_db.id}, limit={limit}, offset={offset}")
    try:
        quotes_db = await crud.list_user_quotes(db=db, user_id=current_user_db.id, limit=limit, offset=offset)
        return [schemas.Quote.model_validate(q) for q in quotes_db]
    except Exception as e:
        logger.error(f"Erreur listage devis pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne listage devis.")

@app.patch("/quotes/{quote_id}/status", response_model=schemas.Quote)
async def update_quote_status_endpoint(
    quote_id: int,
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    status_update: str = Body(..., embed=True, alias="status"),
    db: AsyncSession = Depends(get_db_session)
):
    quote_db_check = await crud.get_quote_by_id(db=db, quote_id=quote_id)
    if not quote_db_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Devis non trouvé")
    
    if quote_db_check.user_id != current_user_db.id and not current_user_db.is_admin:
        logger.warning(f"Accès refusé MAJ statut devis {quote_id} par user {current_user_db.id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à modifier ce devis")

    logger.info(f"MAJ statut devis {quote_id} à '{status_update}' par user {current_user_db.id}")
    try:
        updated_quote_db = await crud.update_quote_status(db=db, quote_id=quote_id, status=status_update)
        return schemas.Quote.model_validate(updated_quote_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur MAJ statut devis {quote_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne MAJ statut devis.")

# ======================================================
# Endpoints: Commandes (Orders)
# ======================================================

@app.post("/orders", response_model=schemas.Order, status_code=status.HTTP_201_CREATED)
async def create_new_order(
    order_request: schemas.OrderCreate,
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Création commande pour user ID: {current_user_db.id}")
    if order_request.user_id != current_user_db.id:
        logger.warning(f"Incohérence user ID création commande (token: {current_user_db.id}, payload: {order_request.user_id}). Utilisation ID token.")
        order_request.user_id = current_user_db.id
    try:
        created_order_db = await crud.create_order(db=db, user_id=current_user_db.id, order_in=order_request)
        try:
            logger.info(f"Tentative envoi email confirmation commande {created_order_db.id} à {current_user_db.email} depuis POST /orders.")
            await services.send_order_confirmation_email(
                user_email=current_user_db.email, 
                order=created_order_db
            )
            logger.info(f"Appel send_order_confirmation_email effectué pour commande {created_order_db.id} depuis POST /orders.")
        except Exception as email_error:
            logger.error(f"Erreur envoi email commande {created_order_db.id} (depuis POST /orders): {email_error}", exc_info=True)
        return schemas.Order.model_validate(created_order_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur création commande pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne création commande.")

@app.get("/orders/{order_id}", response_model=schemas.Order)
async def read_order(
    order_id: int,
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Récupération commande ID: {order_id} pour user {current_user_db.id}")
    try:
        order_db = await crud.get_order_by_id(db=db, order_id=order_id)
        if order_db is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée")
        if order_db.user_id != current_user_db.id:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à cette commande")
        return schemas.Order.model_validate(order_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur récupération commande {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne récupération commande.")

@app.get("/users/me/orders", response_model=List[schemas.Order])
async def list_my_orders(
    limit: int = 20,
    offset: int = 0,
    current_user_db: models.UserDB = Depends(auth.get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Listage commandes pour user {current_user_db.id}, limit={limit}, offset={offset}")
    try:
        orders_db = await crud.list_user_orders(db=db, user_id=current_user_db.id, limit=limit, offset=offset)
        return [schemas.Order.model_validate(o) for o in orders_db]
    except Exception as e:
        logger.error(f"Erreur listage commandes pour user {current_user_db.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne listage commandes.")

@app.patch("/orders/{order_id}/status", response_model=schemas.Order)
async def update_order_status_endpoint(
    order_id: int,
    current_user_db: Annotated[models.UserDB, Depends(auth.get_current_active_user)],
    status_update: str = Body(..., embed=True, alias="status"),
    db: AsyncSession = Depends(get_db_session)
):
    order_db_check = await crud.get_order_by_id(db=db, order_id=order_id)
    if not order_db_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée")

    if order_db_check.user_id != current_user_db.id and not current_user_db.is_admin:
        logger.warning(f"Accès refusé MAJ statut commande {order_id} par user {current_user_db.id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé à modifier cette commande")

    logger.info(f"MAJ statut commande {order_id} à '{status_update}' par user {current_user_db.id}")
    try:
        updated_order_db = await crud.update_order_status(db=db, order_id=order_id, status=status_update)
        return schemas.Order.model_validate(updated_order_db)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erreur MAJ statut commande {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne MAJ statut commande.")

# ======================================================
# Initialisation & Lancement
# ======================================================

# Note: L'ancien endpoint /products_old a été supprimé car marqué deprecated et levait une erreur.

# Lancement (si exécuté directement, pour debug local)
# if __name__ == "__main__":
#     import uvicorn
#     logger.info("Démarrage du serveur Uvicorn pour le développement...")
#     uvicorn.run(app, host="0.0.0.0", port=8000)