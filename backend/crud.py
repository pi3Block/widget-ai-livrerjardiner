import logging
import psycopg2
from psycopg2 import OperationalError, ProgrammingError
from psycopg2.extras import Json # Pour insérer/récupérer JSONB
from psycopg2.pool import SimpleConnectionPool
from fastapi import HTTPException
import random
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
import bcrypt
from datetime import datetime
from pydantic import BaseModel, EmailStr

# --- Imports pour SQLAlchemy & FastCRUD ---
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, join # Pour les requêtes SQLAlchemy directes si besoin
from sqlalchemy.orm import selectinload, joinedload # Pour eager loading
from fastcrud import FastCRUD
from sqlalchemy import func as sql_func, distinct, or_, and_, String as SQLString, cast
from sqlalchemy import update as sqlalchemy_update # Renommer pour éviter conflit avec crud update
from sqlalchemy.future import select as future_select # Pour select avec options
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func # Pour CURRENT_TIMESTAMP

# --- Importer la configuration DB (gardé pour le moment) ---
import config
# --- Importer les modèles SQLAlchemy DB --- 
import models # Contient maintenant uniquement les modèles DB (ex: UserDB, AddressDB)

# --- Importer les Schémas Pydantic --- 
import schemas # Nouveau fichier contenant les schémas Pydantic (ex: User, UserCreate)


logger = logging.getLogger(__name__)

# ======================================================
# Instances FastCRUD
# ======================================================
# Utilisation des modèles DB depuis 'models' et des schémas Pydantic depuis 'schemas'

crud_user = FastCRUD(models.UserDB, schemas.UserCreate, schemas.UserUpdate, schemas.User)
crud_address = FastCRUD(models.AddressDB, schemas.AddressCreate, schemas.AddressUpdate, schemas.Address)
crud_category = FastCRUD(models.CategoryDB, schemas.CategoryCreate, schemas.CategoryUpdate, schemas.Category)
crud_tag = FastCRUD(models.TagDB, schemas.TagCreate, schemas.TagCreate, schemas.Tag) # Utilise TagCreate pour Update aussi, à vérifier
crud_product = FastCRUD(models.ProductDB, schemas.ProductCreate, schemas.ProductUpdate, schemas.Product)
crud_product_variant = FastCRUD(models.ProductVariantDB, schemas.ProductVariantCreate, schemas.ProductVariantUpdate, schemas.ProductVariant)
crud_stock = FastCRUD(models.StockDB, schemas.StockBase, schemas.StockUpdate, schemas.Stock) # Utilise StockBase/Update pour Create/Update
crud_stock_movement = FastCRUD(models.StockMovementDB, schemas.StockMovementCreate, schemas.StockMovementCreate, schemas.StockMovement)
crud_quote = FastCRUD(models.QuoteDB, schemas.QuoteCreate, schemas.QuoteUpdate, schemas.Quote)
crud_quote_item = FastCRUD(models.QuoteItemDB, schemas.QuoteItemCreate, schemas.QuoteItemCreate, schemas.QuoteItem)
crud_order = FastCRUD(models.OrderDB, schemas.OrderCreate, schemas.OrderUpdate, schemas.Order)
crud_order_item = FastCRUD(models.OrderItemDB, schemas.OrderItemCreate, schemas.OrderItemCreate, schemas.OrderItem)

# ======================================================
# Logique CRUD (Avec SQLAlchemy & FastCRUD - Nouvelle)
# ======================================================

# --- CRUD: Users & Authentication (Refactorisé) ---

async def create_user(db: AsyncSession, user_in: schemas.UserCreate) -> models.UserDB:
    """Crée un nouvel utilisateur en utilisant SQLAlchemy et FastCRUD."""
    logger.debug(f"[CRUD_V2] Création utilisateur: {user_in.email}")

    # 1. Vérifier si l'email existe déjà en utilisant FastCRUD (get), retournant un dict ou None
    existing_user = await crud_user.get(db=db, email=user_in.email)
    if existing_user:
        logger.warning(f"[CRUD_V2] Tentative de création d'un utilisateur avec email existant: {user_in.email}")
        raise HTTPException(status_code=409, detail="Un compte avec cet email existe déjà.")

    # 2. Hacher le mot de passe avec bcrypt
    try:
        # Encoder le mot de passe en bytes avant de le hacher
        password_bytes = user_in.password.encode('utf-8')
        # Générer le hash avec bcrypt
        hashed_password_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        # Décoder le hash en string UTF-8 pour le stockage en DB
        hashed_password = hashed_password_bytes.decode('utf-8')
    except Exception as e: # Exception plus générale au cas où
        logger.error(f"[CRUD_V2] Erreur lors du hachage du mot de passe pour {user_in.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la sécurisation du mot de passe.")

    # 3. Préparer les données pour la création (exclure le mot de passe en clair)
    user_data_for_db = user_in.model_dump(exclude={"password"})
    user_data_for_db["password_hash"] = hashed_password

    # --- Workaround pour FastCRUD create attendant .model_dump() --- 
    # Définir un modèle Pydantic temporaire qui correspond aux données
    class _TempUserCreateData(BaseModel):
        email: EmailStr
        name: Optional[str] = None
        password_hash: str
    # ------------------------------------------------------------

    # 4. Créer l'utilisateur avec FastCRUD
    try:
        # Créer une instance du modèle temporaire
        temp_pydantic_object = _TempUserCreateData(**user_data_for_db)

        # Passer l'instance Pydantic à FastCRUD create
        created_user_db = await crud_user.create(db=db, object=temp_pydantic_object)

        # Le commit est géré par la dépendance get_db_session
        # Ajout flush/refresh pour s'assurer que l'objet est à jour si besoin immédiatement après
        await db.flush()
        await db.refresh(created_user_db)

        logger.info(f"[CRUD_V2] Utilisateur créé avec ID: {created_user_db.id} pour email: {created_user_db.email}")
        return created_user_db
    except Exception as e:
        # Le rollback est géré par la dépendance get_db_session
        # Vérifier si c'est une violation de contrainte unique (peut arriver malgré la vérification initiale)
        if "UniqueViolationError" in str(e) or "duplicate key value violates unique constraint" in str(e):
             logger.warning(f"[CRUD_V2] Conflit lors de l'insertion (email déjà existant?): {user_in.email}")
             raise HTTPException(status_code=409, detail="Un compte avec cet email existe déjà (vérification post-insertion).")
        else:
            logger.error(f"[CRUD_V2] Erreur lors de l'insertion de l'utilisateur {user_in.email}: {e}", exc_info=True)
            # Lever une exception pour informer l'appelant et déclencher le rollback
            raise HTTPException(status_code=500, detail="Erreur interne lors de la création de l'utilisateur.")

# Authenticate user retourne un dict, pas un UserDB. À ajuster si besoin.
async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authentifie un utilisateur par email et mot de passe. Retourne un dictionnaire des données utilisateur ou None."""
    logger.debug(f"[CRUD_V2] Tentative d'authentification pour: {email}")

    # 1. Récupérer l'utilisateur par email via FastCRUD (get), retournant un dict ou None
    try:
        user_dict = await crud_user.get(db=db, email=email)
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur DB lors de la recherche de l'utilisateur {email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de l'authentification.")

    if not user_dict:
        logger.warning(f"[AUTH_V2] Utilisateur non trouvé: {email}")
        return None

    # 2. Vérifier le mot de passe
    logger.debug(f"[AUTH_V2_VERIF] Hash lu depuis DB: {user_dict['password_hash']}")
    logger.debug(f"[AUTH_V2_VERIF] Mot de passe reçu: '{password}'")
    password_bytes = password.encode('utf-8')
    hashed_password_bytes = user_dict['password_hash'].encode('utf-8')
    
    if not bcrypt.checkpw(password_bytes, hashed_password_bytes):
        logger.warning(f"[AUTH_V2] Mot de passe incorrect pour: {email}")
        return None

    logger.info(f"[AUTH_V2] Authentification réussie pour: {email} (ID: {user_dict['id']})")
    # 3. Retourner le dictionnaire utilisateur
    return user_dict

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[models.UserDB]:
    """Récupère un objet utilisateur SQLAlchemy par son ID."""
    logger.debug(f"[CRUD_V2] Récupération objet UserDB ID: {user_id}")
    try:
        user_db_object = await db.get(models.UserDB, user_id)
        
        if not user_db_object:
            logger.warning(f"[CRUD_V2] User ID {user_id} non trouvé.")
            return None
        return user_db_object 
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la récupération de l'objet UserDB ID {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération de l'utilisateur.")

# Nouvelle fonction pour charger l'utilisateur avec ses adresses
async def get_user_by_id_with_addresses(db: AsyncSession, user_id: int) -> Optional[models.UserDB]:
    """Récupère un utilisateur par ID avec ses adresses pré-chargées (eager loading)."""
    logger.debug(f"[CRUD_V2] Récupération UserDB ID {user_id} avec adresses")
    try:
        stmt = select(models.UserDB).options(selectinload(models.UserDB.addresses)).where(models.UserDB.id == user_id)
        result = await db.execute(stmt)
        user_db_object = result.scalar_one_or_none()
        if not user_db_object:
            logger.warning(f"[CRUD_V2] User ID {user_id} non trouvé lors de la récupération avec adresses.")
            return None
        return user_db_object
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la récupération UserDB ID {user_id} avec adresses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération des données utilisateur.")

# ======================================================
# CRUD Operations for Addresses
# ======================================================

# --- Create Address ---
async def create_user_address(db: AsyncSession, user_id: int, address_in: schemas.AddressCreate) -> models.AddressDB:
    """Crée une nouvelle adresse pour un utilisateur."""
    user = await get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")

    existing_addresses_stmt = select(sql_func.count(models.AddressDB.id)).where(models.AddressDB.user_id == user_id)
    address_count_result = await db.execute(existing_addresses_stmt)
    address_count = address_count_result.scalar_one()
    set_as_default = address_count == 0

    db_address = models.AddressDB(
        **address_in.model_dump(),
        user_id=user_id,
        is_default=set_as_default
    )
    db.add(db_address)
    # Commit et refresh sont gérés par la session, mais on peut flush pour obtenir l'ID si nécessaire avant commit
    await db.flush() 
    await db.refresh(db_address)
    return db_address

# --- Get Addresses ---
async def get_user_addresses(db: AsyncSession, user_id: int) -> List[models.AddressDB]:
    """Récupère toutes les adresses d'un utilisateur."""
    stmt = select(models.AddressDB).where(models.AddressDB.user_id == user_id).order_by(models.AddressDB.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())

# --- Get Single Address (helper internal) ---
async def get_address_by_id(db: AsyncSession, address_id: int) -> Optional[models.AddressDB]:
    """Récupère une adresse par son ID."""
    return await db.get(models.AddressDB, address_id)

# --- Set Default Address ---
async def set_default_address(db: AsyncSession, user_id: int, address_id_to_set: int) -> None:
    """Définit une adresse comme adresse par défaut pour l'utilisateur."""
    address_to_set = await get_address_by_id(db, address_id_to_set)
    if not address_to_set or address_to_set.user_id != user_id:
        raise HTTPException(status_code=404, detail=f"Address with id {address_id_to_set} not found or does not belong to user {user_id}")

    stmt_update_others = (
        update(models.AddressDB)
        .where(models.AddressDB.user_id == user_id)
        .values(is_default=False)
    )
    await db.execute(stmt_update_others)
    address_to_set.is_default = True
    db.add(address_to_set)
    # Le commit est géré par la session
    await db.flush() # Flush pour que les changements soient envoyés avant commit

# --- Update Address ---
async def update_user_address(
    db: AsyncSession,
    user_id: int,
    address_id: int,
    address_in: schemas.AddressUpdate
) -> Optional[models.AddressDB]:
    """Met à jour une adresse existante d'un utilisateur via FastCRUD."""
    logger.debug(f"[CRUD_V3] Tentative MAJ adresse ID {address_id} pour user ID {user_id} via FastCRUD")
    db_address = await get_address_by_id(db, address_id)

    if not db_address or db_address.user_id != user_id:
        logger.warning(f"[CRUD_V3] Adresse {address_id} non trouvée ou n'appartient pas à user {user_id} pour MAJ.")
        return None

    update_data = address_in.model_dump(exclude_unset=True)
    if not update_data:
        logger.debug(f"[CRUD_V3] Aucune donnée à mettre à jour pour adresse {address_id}. Retour objet actuel.")
        return db_address

    try:
        updated_address_db = await crud_address.update(db=db, object=update_data, id=address_id)
        logger.info(f"[CRUD_V3] Adresse ID {address_id} mise à jour avec succès.")
        return updated_address_db
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur FastCRUD lors MAJ adresse {address_id} pour user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la mise à jour de l'adresse.")

# --- Delete Address ---
async def delete_user_address(db: AsyncSession, user_id: int, address_id: int) -> bool:
    """Supprime une adresse d'un utilisateur via FastCRUD, avec vérifications."""
    logger.debug(f"[CRUD_V3] Tentative suppression adresse ID {address_id} pour user ID {user_id} via FastCRUD")
    db_address = await get_address_by_id(db, address_id)

    if not db_address or db_address.user_id != user_id:
        logger.warning(f"[CRUD_V3] Adresse {address_id} non trouvée ou n'appartient pas à user {user_id} pour suppression.")
        raise HTTPException(status_code=404, detail=f"Address with id {address_id} not found or does not belong to user {user_id}")

    if db_address.is_default:
        logger.warning(f"[CRUD_V3] Tentative de suppression de l'adresse par défaut {address_id} pour user {user_id}.")
        raise HTTPException(status_code=400, detail="Cannot delete the default address. Please set another address as default first.")

    order_check_stmt = select(sql_func.count(models.OrderDB.id)).where(
        or_(
            models.OrderDB.delivery_address_id == address_id,
            models.OrderDB.billing_address_id == address_id
        )
    )
    order_count_result = await db.execute(order_check_stmt)
    order_count = order_count_result.scalar_one()

    if order_count > 0:
        logger.warning(f"[CRUD_V3] Tentative de suppression de l'adresse {address_id} utilisée dans {order_count} commandes pour user {user_id}.")
        raise HTTPException(status_code=400, detail=f"Cannot delete address with id {address_id} as it is used in {order_count} existing order(s).")

    try:
        await crud_address.delete(db=db, id=address_id)
        logger.info(f"[CRUD_V3] Adresse ID {address_id} supprimée avec succès pour user {user_id}.")
        return True
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur FastCRUD lors suppression adresse {address_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la suppression de l'adresse.")

# ======================================================
# CRUD Operations for Categories & Tags
# ======================================================

async def create_category(db: AsyncSession, category_in: schemas.CategoryCreate) -> models.CategoryDB:
    """Crée une nouvelle catégorie en utilisant FastCRUD."""
    logger.debug(f"[CRUD_V3] Création catégorie: {category_in.name}")
    try:
        created_category_db = await crud_category.create(db=db, object=category_in)
        logger.info(f"[CRUD_V3] Catégorie '{created_category_db.name}' créée avec ID: {created_category_db.id}")
        return created_category_db
    except Exception as e:
        if "UniqueViolationError" in str(e) or "duplicate key value violates unique constraint" in str(e):
            logger.warning(f"[CRUD_V3] Tentative de création de la catégorie '{category_in.name}' qui existe déjà.")
            raise HTTPException(status_code=409, detail=f"La catégorie '{category_in.name}' existe déjà.")
        else:
            logger.error(f"[CRUD_V3] Erreur lors de la création de la catégorie '{category_in.name}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne lors de la création de la catégorie.")

async def get_category(db: AsyncSession, category_id: int) -> Optional[models.CategoryDB]:
    """Récupère une catégorie par son ID en utilisant FastCRUD (retourne le modèle DB)."""
    logger.debug(f"[CRUD_V3] Récupération catégorie ID: {category_id} via FastCRUD (modèle DB)")
    try:
        category_db = await crud_category.get(db=db, id=category_id, return_as_model=True, schema_to_select=schemas.Category)
        if not category_db:
            logger.warning(f"[CRUD_V3] Catégorie ID {category_id} non trouvée.")
            return None
        return category_db
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur lors de la récupération de la catégorie ID {category_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération de la catégorie.")

async def list_categories(
    db: AsyncSession, 
    limit: int = 100, 
    offset: int = 0, 
    sort_by: Optional[str] = None, 
    sort_desc: bool = False,
    filters: Optional[Dict[str, Any]] = None
) -> Tuple[List[models.CategoryDB], int]:
    """Liste les catégories avec filtres, tri et pagination, retourne les modèles DB et le compte total."""
    logger.debug(f"[CRUD_V3] Listage catégories: limit={limit}, offset={offset}, sort={sort_by}, desc={sort_desc}, filters={filters}")
    try:
        # Log avant unpacking pour voir ce que get_multi retourne exactement
        raw_result = await crud_category.get_multi(
            db=db,
            offset=offset,
            limit=limit,
            sort_by=sort_by,
            sort_desc=sort_desc,
            filter=filters # Passer les filtres directement à FastCRUD
        )
        logger.debug(f"[CRUD_V3] Raw result from get_multi: Type={type(raw_result)}, Value={raw_result}")

        # Tentative d'unpacking basé sur l'hypothèse (List[Model], count)
        # À AJUSTER EN FONCTION DU LOG CI-DESSUS
        if isinstance(raw_result, tuple) and len(raw_result) == 2 and isinstance(raw_result[0], list) and isinstance(raw_result[1], int):
            categories_db, total_count = raw_result
            logger.debug(f"[CRUD_V3] Unpacking réussi (Tuple): {len(categories_db)} items, Count={total_count}")
        elif isinstance(raw_result, dict) and 'data' in raw_result and 'total_count' in raw_result:
             # Fallback si get_multi retourne un dict même sans return_as_model=True
             categories_db = raw_result['data']
             total_count = raw_result['total_count']
             logger.debug(f"[CRUD_V3] Unpacking réussi (Dict): {len(categories_db)} items, Count={total_count}")
             if not isinstance(total_count, int):
                 logger.error(f"[CRUD_V3] Le 'total_count' du dict n'est pas un entier: {total_count}")
                 # Essayer de recalculer le count si possible
                 count_query = select(sql_func.count()).select_from(models.CategoryDB).filter_by(**filters if filters else {})
                 count_res = await db.execute(count_query)
                 total_count = count_res.scalar_one_or_none() or 0
                 logger.warning(f"[CRUD_V3] Recalculated total_count: {total_count}")
        else:
            logger.error(f"[CRUD_V3] Résultat inattendu de get_multi. Impossible d'unpacker. Type: {type(raw_result)}")
            # Retourner une liste vide et 0 pour éviter crash, mais indique un problème
            categories_db = []
            total_count = 0 

        # S'assurer que total_count est un entier
        if not isinstance(total_count, int):
             logger.warning(f"[CRUD_V3] total_count n'est pas un entier après unpacking/fallback: {total_count}. Utilisation de 0.")
             total_count = 0

        logger.debug(f"[CRUD_V3] Final values: {len(categories_db)} catégories (modèles DB) récupérées. Total count: {total_count}")
        return categories_db, total_count
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur lors du listage des catégories (DB): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération des catégories.")

async def get_tag_by_name(db: AsyncSession, name: str) -> Optional[models.TagDB]:
    """Récupère un tag par son nom en utilisant FastCRUD."""
    logger.debug(f"[CRUD_V3] Recherche tag par nom: {name}")
    try:
        # Utiliser get avec filtre par argument nommé et retour modèle DB
        tag_db = await crud_tag.get(db=db, name=name, return_as_model=True, schema_to_select=schemas.Tag)
        return tag_db # Retourne None si non trouvé
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur lors de la recherche du tag '{name}': {e}", exc_info=True)
        raise # Remonter l'exception pour la gestion transactionnelle

async def create_tag(db: AsyncSession, tag_in: schemas.TagCreate) -> models.TagDB:
    """Crée un nouveau tag en utilisant FastCRUD. Gère l'unicité."""
    logger.debug(f"[CRUD_V3] Tentative de création tag: {tag_in.name}")
    try:
        created_tag_db = await crud_tag.create(db=db, object=tag_in)
        logger.debug(f"[CRUD_V3] Tag '{tag_in.name}' créé avec ID {created_tag_db.id}")
        # Flush/refresh pour s'assurer que l'objet est complet si besoin immédiatement
        await db.flush()
        await db.refresh(created_tag_db)
        return created_tag_db
    except Exception as e:
        if "UniqueViolationError" in str(e) or "duplicate key value violates unique constraint" in str(e):
            logger.warning(f"[CRUD_V3] Tentative de création du tag '{tag_in.name}' qui existe déjà.")
            existing_tag = await get_tag_by_name(db, tag_in.name)
            if existing_tag:
                return existing_tag
            else:
                logger.error(f"[CRUD_V3] Erreur Integrity lors création tag '{tag_in.name}', mais impossible de le récupérer.")
                raise HTTPException(status_code=500, detail=f"Erreur lors de la création/récupération du tag '{tag_in.name}'.")
        else:
            logger.error(f"[CRUD_V3] Erreur inattendue lors de la création du tag '{tag_in.name}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne lors de la création du tag.")

# --- CRUD: Products & Variants (Refactorisé - Part 1) ---

async def create_product(db: AsyncSession, product_in: schemas.ProductCreate) -> models.ProductDB:
    """Crée un nouveau produit de base en utilisant SQLAlchemy/FastCRUD."""
    logger.debug(f"[CRUD_V3] Création du produit : {product_in.name} via FastCRUD")
    try:
        created_product_db = await crud_product.create(db=db, object=product_in)
        await db.flush()
        await db.refresh(created_product_db)
        logger.info(f"[CRUD_V3] Produit créé avec ID: {created_product_db.id}")
        return created_product_db
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur lors de la création du produit '{product_in.name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la création du produit.")

async def get_product_variant_by_id(db: AsyncSession, variant_id: int) -> Optional[models.ProductVariantDB]:
    """Récupère une variation par son ID, incluant ses tags (eager loading)."""
    logger.debug(f"[CRUD_V3] Récupération variant ID {variant_id} via FastCRUD avec tags")
    try:
        options = [selectinload(models.ProductVariantDB.tags)]
        variant_db = await crud_product_variant.get(
            db=db, 
            id=variant_id, 
            schema_to_select=schemas.ProductVariant, # Utiliser schéma Pydantic
            return_as_model=True, 
            options=options
        )
        if not variant_db:
            logger.warning(f"[CRUD_V3] Variation ID {variant_id} non trouvée.")
            return None
        return variant_db
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur FastCRUD get variant ID {variant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération de la variation.")

async def get_product_variant_by_sku(db: AsyncSession, sku: str) -> Optional[models.ProductVariantDB]:
    """Récupère une variation de produit par son SKU, incluant ses tags (eager loading)."""
    logger.debug(f"[CRUD_V3] Recherche de la variation SKU: {sku} via FastCRUD avec tags")
    try:
        options = [selectinload(models.ProductVariantDB.tags)]
        variant_db = await crud_product_variant.get(
            db=db, 
            sku=sku, 
            schema_to_select=schemas.ProductVariant, # Utiliser schéma Pydantic
            return_as_model=True, 
            options=options
        )
        if not variant_db:
            logger.warning(f"[CRUD_V3] Variation SKU {sku} non trouvée.")
            return None
        return variant_db
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur FastCRUD get_by_field SKU {sku}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération de la variation.")

# --- CRUD: Stock & Movements (Refactorisé) ---

async def get_stock_for_variant(db: AsyncSession, variant_id: int) -> Optional[models.StockDB]:
    """Récupère l'objet StockDB pour une variation donnée."""
    logger.debug(f"[CRUD_V3] Vérification stock pour variant_id: {variant_id} via FastCRUD")
    try:
        stock_db = await crud_stock.get(db=db, id=variant_id, return_as_model=True, schema_to_select=schemas.Stock)
        if not stock_db:
            logger.warning(f"[CRUD_V3] Enregistrement stock non trouvé pour variant_id {variant_id}")
            return None
        logger.debug(f"[CRUD_V3] Stock trouvé pour variant_id {variant_id}: qte={stock_db.quantity}")
        return stock_db
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur FastCRUD get stock pour variant {variant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la vérification du stock.")

async def update_stock_for_variant(db: AsyncSession, variant_id: int, quantity_change: int) -> models.StockDB:
    """Met à jour le stock pour une variation et retourne l'objet StockDB mis à jour."""
    logger.debug(f"[CRUD_V2][TX] Mise à jour stock pour variant_id: {variant_id}, changement: {quantity_change}")
    stmt = (
        sqlalchemy_update(models.StockDB)
        .where(models.StockDB.product_variant_id == variant_id)
        .values(
            quantity=models.StockDB.quantity + quantity_change,
            last_updated=datetime.now(datetime.timezone.utc)
            )
        .returning(models.StockDB.quantity, models.StockDB.product_variant_id)
    )
    try:
        result = await db.execute(stmt)
        updated_row = result.fetchone()
        if updated_row is None:
            logger.error(f"[CRUD_V2][TX] Tentative de mise à jour du stock pour variant_id {variant_id} non trouvé.")
            raise HTTPException(status_code=404, detail=f"Stock non trouvé pour la variation ID {variant_id}.")

        new_quantity = updated_row[0]
        if new_quantity < 0:
            logger.error(f"[CRUD_V2][TX] Stock insuffisant pour variant_id {variant_id}. Rollback nécessaire.")
            raise ValueError("Stock insuffisant.")

        logger.debug(f"[CRUD_V2][TX] Stock mis à jour pour variant_id {variant_id}. Nouvelle quantité: {new_quantity}")
        updated_stock_db = await get_stock_for_variant(db, variant_id)
        if not updated_stock_db:
             raise HTTPException(status_code=500, detail="Erreur interne: Impossible de récupérer le stock après mise à jour.")
        return updated_stock_db
    except ValueError as ve:
         logger.error(f"[CRUD_V2][TX] Erreur métier lors de la mise à jour du stock: {ve}")
         raise HTTPException(status_code=409, detail=str(ve))
    except Exception as e:
        logger.error(f"[CRUD_V2][TX] Erreur DB/inattendue lors de la mise à jour du stock pour variant_id {variant_id}: {e}", exc_info=True)
        raise

async def record_stock_movement(db: AsyncSession, movement_in: schemas.StockMovementCreate) -> models.StockMovementDB:
    """Enregistre un mouvement de stock."""
    logger.debug(f"[CRUD_V3][TX] Enregistrement mouvement stock: variant={movement_in.product_variant_id}, qty_change={movement_in.quantity_change}, type={movement_in.movement_type}, order_item={movement_in.order_item_id}")
    try:
        created_movement_db = await crud_stock_movement.create(db=db, object=movement_in)
        await db.flush()
        await db.refresh(created_movement_db)
        logger.debug(f"[CRUD_V3][TX] Mouvement de stock ID {created_movement_db.id} enregistré.")
        return created_movement_db
    except Exception as e:
        logger.error(f"[CRUD_V3][TX] Erreur FastCRUD lors de l'enregistrement du mouvement de stock: {e}", exc_info=True)
        raise # Remonter l'exception

# --- CRUD: Quotes & Quote Items (Refactorisé) ---

async def create_quote(db: AsyncSession, user_id: int, quote_in: schemas.QuoteCreate) -> models.QuoteDB:
    """Crée un nouveau devis avec ses lignes, utilisant FastCRUD pour la récupération."""
    logger.debug(f"[CRUD_V3] Création devis user {user_id} ({len(quote_in.items)} items) - Utilisation FastCRUD pour lookup variants")
    user = await get_user_by_id(db, user_id)
    if not user:
        logger.warning(f"[CRUD_V3] Utilisateur {user_id} non trouvé pour création devis.")
        raise HTTPException(status_code=404, detail=f"Utilisateur ID {user_id} non trouvé.")

    quote_data = quote_in.model_dump(exclude={'items'})
    quote_db = models.QuoteDB(**quote_data, user_id=user_id) 
    db.add(quote_db)
    await db.flush()
    await db.refresh(quote_db)
    logger.debug(f"[CRUD_V3] Devis DB créé avec ID: {quote_db.id}")

    total_quote_price = Decimal("0.0")
    items_to_add = []
    variants_cache = {}

    for item_in in quote_in.items:
        variant_id = item_in.product_variant_id
        if variant_id not in variants_cache:
            variant_db = await get_product_variant_by_id(db, variant_id)
            if not variant_db:
                logger.error(f"[CRUD_V3] Variation ID {variant_id} non trouvée pour devis {quote_db.id}.")
                raise HTTPException(status_code=404, detail=f"Variation produit ID {variant_id} non trouvée.")
            variants_cache[variant_id] = variant_db
        else:
            variant_db = variants_cache[variant_id]

        item_price = variant_db.price * item_in.quantity
        total_quote_price += item_price
        
        # Utiliser le schéma Pydantic pour créer l'item
        quote_item_data = item_in.model_dump()
        quote_item_db = models.QuoteItemDB(
            **quote_item_data,
            quote_id=quote_db.id,
            unit_price=variant_db.price # Prix au moment du devis
        )
        items_to_add.append(quote_item_db)

    db.add_all(items_to_add)
    quote_db.total_price = total_quote_price # Mettre à jour le prix total du devis
    db.add(quote_db)
    await db.flush()
    await db.refresh(quote_db)
    for item in items_to_add:
        await db.refresh(item)

    logger.info(f"[CRUD_V3] Devis ID {quote_db.id} créé pour user {user_id} avec {len(items_to_add)} items, total={total_quote_price:.2f}")
    return quote_db

# --- CRUD: Orders & Order Items (Refactorisé) ---

async def create_order(db: AsyncSession, user_id: int, order_in: schemas.OrderCreate) -> models.OrderDB:
    """Crée une nouvelle commande, vérifie le stock, met à jour le stock et enregistre les mouvements."""
    logger.debug(f"[CRUD_V3][TX] Début création commande pour user {user_id} ({len(order_in.items)} items)")

    # Vérifications initiales (utilisateur, adresses)
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Utilisateur {user_id} non trouvé.")
    delivery_address = await get_address_by_id(db, order_in.delivery_address_id)
    billing_address = await get_address_by_id(db, order_in.billing_address_id)
    if not delivery_address or delivery_address.user_id != user_id:
        raise HTTPException(status_code=400, detail="Adresse de livraison invalide ou n'appartient pas à l'utilisateur.")
    if not billing_address or billing_address.user_id != user_id:
        raise HTTPException(status_code=400, detail="Adresse de facturation invalide ou n'appartient pas à l'utilisateur.")

    order_data = order_in.model_dump(exclude={'items', 'total_price'}) # Exclure items et total_price
    order_db = models.OrderDB(**order_data, user_id=user_id, total_price=Decimal("0.0")) # Initialiser total_price
    db.add(order_db)
    await db.flush() # Flush pour obtenir l'ID de la commande
    logger.debug(f"[CRUD_V3][TX] OrderDB pré-créé avec ID: {order_db.id}")

    total_order_price = Decimal("0.0")
    variants_cache = {}
    stock_updates = [] # Liste des (variant_id, quantity_change)
    items_to_add = []

    # 1. Vérifier la disponibilité et préparer les items
    for item_in in order_in.items:
        variant_id = item_in.product_variant_id
        quantity_requested = item_in.quantity

        if quantity_requested <= 0:
            raise HTTPException(status_code=400, detail=f"Quantité invalide ({quantity_requested}) pour variation ID {variant_id}.")

        # Récupérer la variation (avec cache)
        if variant_id not in variants_cache:
            variant_db = await get_product_variant_by_id(db, variant_id)
            if not variant_db:
                raise HTTPException(status_code=404, detail=f"Variation produit ID {variant_id} non trouvée.")
            variants_cache[variant_id] = variant_db
        else:
            variant_db = variants_cache[variant_id]

        # Vérifier le stock (simplifié, utilise la fonction get_stock)
        stock_db = await get_stock_for_variant(db, variant_id)
        current_stock = stock_db.quantity if stock_db else 0
        if current_stock < quantity_requested:
            logger.warning(f"[CRUD_V3][TX] Stock insuffisant pour SKU {variant_db.sku} (ID: {variant_id}). Demandé: {quantity_requested}, Disponible: {current_stock}")
            raise HTTPException(status_code=409, detail=f"Stock insuffisant pour {variant_db.sku}. Disponible: {current_stock}")

        # Préparer l'item de commande
        item_price = variant_db.price * quantity_requested
        total_order_price += item_price
        order_item_data = item_in.model_dump()
        order_item_db = models.OrderItemDB(
            **order_item_data,
            order_id=order_db.id,
            unit_price=variant_db.price # Prix au moment de la commande
        )
        items_to_add.append(order_item_db)
        stock_updates.append((variant_id, -quantity_requested)) # Négatif pour sortie de stock

    # 2. Ajouter les items à la session et mettre à jour le prix total de la commande
    db.add_all(items_to_add)
    order_db.total_price = total_order_price
    db.add(order_db)
    await db.flush() # Flush pour obtenir les IDs des OrderItemDB
    logger.debug(f"[CRUD_V3][TX] {len(items_to_add)} OrderItemDB ajoutés à la session pour Order ID {order_db.id}. Total Price: {total_order_price:.2f}")

    # Créer un mapping ID OrderItem pour les mouvements de stock
    order_item_id_map = {item.product_variant_id: item.id for item in items_to_add}

    # 3. Mettre à jour le stock et enregistrer les mouvements
    stock_movements_to_add = []
    for variant_id, quantity_change in stock_updates:
        try:
            # Utiliser update_stock_for_variant qui gère la logique atomique et vérifie le stock négatif
            await update_stock_for_variant(db, variant_id, quantity_change)
            logger.debug(f"[CRUD_V3][TX] Stock mis à jour pour variant ID {variant_id} (change: {quantity_change})")

            # Enregistrer le mouvement de stock
            order_item_id = order_item_id_map.get(variant_id)
            movement_in = schemas.StockMovementCreate(
                product_variant_id=variant_id,
                quantity_change=quantity_change, # Négatif ici
                movement_type='sale',
                related_order_id=order_db.id,
                order_item_id=order_item_id,
                notes=f"Order ID: {order_db.id}"
            )
            # Utiliser la fonction CRUD pour créer le mouvement
            await record_stock_movement(db, movement_in=movement_in)
            logger.debug(f"[CRUD_V3][TX] Mouvement de stock enregistré pour variant ID {variant_id}")

        except ValueError as ve: # Capturer l'erreur "Stock insuffisant" levée par update_stock_for_variant
            logger.error(f"[CRUD_V3][TX] Conflit de stock détecté pendant la mise à jour pour variant ID {variant_id}: {ve}")
            raise HTTPException(status_code=409, detail=str(ve))
        except Exception as e:
            logger.error(f"[CRUD_V3][TX] Erreur lors de la mise à jour du stock ou enregistrement mouvement pour variant {variant_id}: {e}", exc_info=True)
            raise # Remonter pour rollback

    # 4. Rafraîchir les objets (si nécessaire pour la réponse)
    await db.refresh(order_db)
    for item in items_to_add:
        await db.refresh(item)

    logger.info(f"[CRUD_V3][TX] Commande ID {order_db.id} créée avec succès pour user {user_id}. Total: {total_order_price:.2f}")
    # Retourner l'objet OrderDB complet (FastAPI le convertira via le response_model)
    return order_db

# --- CRUD: Products (Suite - Get/List/Update/Delete) ---

async def get_product_by_id(db: AsyncSession, product_id: int) -> Optional[models.ProductDB]:
    """Récupère un produit par son ID, chargeant ses variations et leur stock."""
    logger.debug(f"[CRUD_V3] Récupération produit ID: {product_id} avec variations et stock")
    try:
        options = [
            selectinload(models.ProductDB.variants).selectinload(models.ProductVariantDB.stock),
            selectinload(models.ProductDB.variants).selectinload(models.ProductVariantDB.tags),
            selectinload(models.ProductDB.category)
        ]
        product_db = await crud_product.get(
            db=db,
            id=product_id,
            options=options,
            return_as_model=True,
            schema_to_select=schemas.Product # Utiliser le schéma Pydantic complet
        )
        return product_db
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur lors de la récupération du produit ID {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération du produit.")

async def list_products_with_variants(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    category_id: Optional[int] = None,
    tag_names: Optional[List[str]] = None,
    search_term: Optional[str] = None
) -> List[models.ProductDB]:
    """Liste les produits avec leurs variations, appliquant filtres et pagination."""
    logger.debug(f"[CRUD_V3] Listage produits avec filtres: cat={category_id}, tags={tag_names}, search={search_term}, limit={limit}, offset={offset}")

    query = select(models.ProductDB).options(
        selectinload(models.ProductDB.variants).selectinload(models.ProductVariantDB.stock),
        selectinload(models.ProductDB.variants).selectinload(models.ProductVariantDB.tags),
        selectinload(models.ProductDB.category)
    ).distinct()

    # Filtrage
    if category_id:
        query = query.where(models.ProductDB.category_id == category_id)
    if search_term or tag_names:
        search_ilike = f"%{search_term}%"
        query = query.join(models.ProductVariantDB, models.ProductDB.id == models.ProductVariantDB.product_id)
        query = query.where(
            or_(
                models.ProductDB.name.ilike(search_ilike),
                models.ProductDB.base_description.ilike(search_ilike),
                models.ProductVariantDB.sku.ilike(search_ilike),
                # Recherche dans les attributs JSONB (simple, peut être optimisé)
                cast(models.ProductVariantDB.attributes, SQLString).ilike(search_ilike)
            )
        )
    if tag_names:
        query = query.join(product_variant_tags_table, models.ProductVariantDB.id == product_variant_tags_table.c.product_variant_id)
        query = query.join(models.TagDB, product_variant_tags_table.c.tag_id == models.TagDB.id)
        query = query.where(models.TagDB.name.in_(tag_names))

    # Tri, Pagination et Exécution
    query = query.order_by(models.ProductDB.id).limit(limit).offset(offset)
    result = await db.execute(query)
    products_db = list(result.scalars().all())
    logger.debug(f"[CRUD_V3] {len(products_db)} produits récupérés pour la page.")
    return products_db

async def count_products_with_variants(
    db: AsyncSession,
    category_id: Optional[int] = None,
    tag_names: Optional[List[str]] = None,
    search_term: Optional[str] = None
) -> int:
    """Compte le nombre total de produits uniques correspondant aux filtres."""
    logger.debug(f"[CRUD_V3] Comptage produits avec filtres: cat={category_id}, tags={tag_names}, search={search_term}")

    # Utiliser une sous-requête pour obtenir les IDs uniques des produits filtrés
    subquery = select(models.ProductDB.id).distinct()
    needs_join = False

    if category_id:
        subquery = subquery.where(models.ProductDB.category_id == category_id)
    
    if search_term or tag_names:
        subquery = subquery.join(models.ProductVariantDB, models.ProductDB.id == models.ProductVariantDB.product_id)
        needs_join = True

    if search_term:
        search_ilike = f"%{search_term}%"
        subquery = subquery.where(
            or_(
                models.ProductDB.name.ilike(search_ilike),
                models.ProductDB.base_description.ilike(search_ilike),
                models.ProductVariantDB.sku.ilike(search_ilike),
                cast(models.ProductVariantDB.attributes, SQLString).ilike(search_ilike)
            )
        )

    if tag_names:
        subquery = subquery.join(product_variant_tags_table, models.ProductVariantDB.id == product_variant_tags_table.c.product_variant_id)
        subquery = subquery.join(models.TagDB, product_variant_tags_table.c.tag_id == models.TagDB.id)
        subquery = subquery.where(models.TagDB.name.in_(tag_names))

    # Compter les résultats de la sous-requête
    count_query = select(sql_func.count()).select_from(subquery.alias())
    result = await db.execute(count_query)
    total_count = result.scalar_one()
    logger.debug(f"[CRUD_V3] Total produits trouvés: {total_count}")
    return total_count

async def create_product_variant(
    db: AsyncSession,
    variant_in: schemas.ProductVariantCreate
) -> models.ProductVariantDB:
    """Crée une nouvelle variation de produit, gère le stock initial et les tags."""
    logger.debug(f"[CRUD_V3] Création variation: SKU={variant_in.sku} pour produit ID={variant_in.product_id}")

    # Vérifier que le produit parent existe
    product_db = await crud_product.get(db=db, id=variant_in.product_id)
    if not product_db:
        raise HTTPException(status_code=404, detail=f"Produit parent ID {variant_in.product_id} non trouvé.")

    # Vérifier l'unicité du SKU
    existing_variant = await crud_product_variant.get(db=db, sku=variant_in.sku)
    if existing_variant:
        raise HTTPException(status_code=409, detail=f"SKU '{variant_in.sku}' existe déjà.")

    variant_data = variant_in.model_dump(exclude={'initial_stock', 'tag_names'})
    created_variant_db = await crud_product_variant.create(db=db, object=variant_data)
    await db.flush()
    await db.refresh(created_variant_db)
    logger.info(f"[CRUD_V3] Variation créée avec ID: {created_variant_db.id}")

    # Gérer le stock initial
    if variant_in.initial_stock is not None and variant_in.initial_stock > 0:
        stock_db = models.StockDB(product_variant_id=created_variant_db.id, quantity=variant_in.initial_stock)
        db.add(stock_db)
        logger.debug(f"[CRUD_V3] Stock initial ({variant_in.initial_stock}) créé pour variation ID {created_variant_db.id}")

    # Gérer les tags
    if variant_in.tag_names:
        tags_to_assign = []
        for tag_name in set(variant_in.tag_names): # Utiliser set pour éviter doublons
            tag_db = await get_tag_by_name(db, tag_name)
            if not tag_db:
                # Créer le tag s'il n'existe pas
                tag_db = await create_tag(db, schemas.TagCreate(name=tag_name))
            tags_to_assign.append(tag_db)
        
        created_variant_db.tags = tags_to_assign
        db.add(created_variant_db)
        logger.debug(f"[CRUD_V3] Tags {variant_in.tag_names} assignés à variation ID {created_variant_db.id}")

    await db.flush()
    await db.refresh(created_variant_db)
    # Charger explicitement les tags pour le retour (si nécessaire)
    # await db.refresh(created_variant_db, attribute_names=['tags'])

    return created_variant_db

# TODO: Implémenter update_product, delete_product, update_variant, delete_variant etc.
