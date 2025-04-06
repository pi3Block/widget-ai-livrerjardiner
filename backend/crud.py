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

# --- Imports pour SQLAlchemy & FastCRUD ---
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, join # Pour les requêtes SQLAlchemy directes si besoin
from sqlalchemy.orm import selectinload, joinedload # Pour eager loading
from fastcrud import FastCRUD
from sqlalchemy import func as sql_func, distinct, or_, and_, String as SQLString, cast
from sqlalchemy import update as sqlalchemy_update # Renommer pour éviter conflit avec crud update
from sqlalchemy.future import select as future_select # Pour select avec options

# --- Importer la configuration DB (gardé pour le moment) ---
import config
# --- Importer les modèles Pydantic V3 et SQLAlchemy DB ---
import models
from models import (
    User, UserCreate, UserDB,
    Address, AddressCreate, AddressDB,
    Category, CategoryCreate, CategoryDB,
    Tag, TagCreate, TagDB,
    Product, ProductCreate, ProductDB,
    ProductVariant, ProductVariantCreate, ProductVariantDB,
    Stock, StockDB,
    StockMovement, StockMovementCreate, StockMovementDB,
    Quote, QuoteCreate, QuoteDB,
    QuoteItem, QuoteItemCreate, QuoteItemDB,
    Order, OrderCreate, OrderDB,
    OrderItem, OrderItemCreate, OrderItemDB
)
# --- Importer la dépendance de session DB --- 
# Non nécessaire ici, sera injectée dans les endpoints de main.py
# from database import get_db_session 

logger = logging.getLogger(__name__)

# ======================================================
# Instances FastCRUD
# ======================================================
# Pour chaque modèle DB, on crée une instance FastCRUD en liant :
# - le modèle SQLAlchemy (model=...DB)
# - le schéma Pydantic pour la création (create_schema=...Create)
# - le schéma Pydantic pour la mise à jour (update_schema=...Update - à créer si besoin)
# - le schéma Pydantic pour la lecture (read_schema=...)

crud_user = FastCRUD(UserDB, UserCreate, models.UserUpdate, User)
crud_address = FastCRUD(AddressDB, AddressCreate, models.AddressUpdate, Address)
crud_category = FastCRUD(CategoryDB, CategoryCreate, models.CategoryUpdate, Category)
crud_tag = FastCRUD(TagDB, TagCreate, TagCreate, Tag)
crud_product = FastCRUD(ProductDB, ProductCreate, models.ProductUpdate, Product)
crud_product_variant = FastCRUD(ProductVariantDB, ProductVariantCreate, models.ProductVariantUpdate, ProductVariant)
crud_stock = FastCRUD(StockDB, models.StockBase, models.StockBase, models.Stock)
crud_stock_movement = FastCRUD(StockMovementDB, StockMovementCreate, StockMovementCreate, StockMovement)
crud_quote = FastCRUD(QuoteDB, QuoteCreate, models.QuoteUpdate, Quote)
crud_quote_item = FastCRUD(QuoteItemDB, QuoteItemCreate, QuoteItemCreate, QuoteItem)
crud_order = FastCRUD(OrderDB, OrderCreate, models.OrderUpdate, Order)
crud_order_item = FastCRUD(OrderItemDB, OrderItemCreate, OrderItemCreate, OrderItem)

# ======================================================
# Logique CRUD (Avec SQLAlchemy & FastCRUD - Nouvelle)
# ======================================================

# --- CRUD: Users & Authentication (Refactorisé) ---

async def create_user(db: AsyncSession, user_in: models.UserCreate) -> models.UserDB:
    """Crée un nouvel utilisateur en utilisant SQLAlchemy et FastCRUD."""
    logger.debug(f"[CRUD_V2] Création utilisateur: {user_in.email}")

    # 1. Vérifier si l'email existe déjà en utilisant FastCRUD (get_multi avec filtre par argument nommé)
    existing_user_result = await crud_user.get_multi(db=db, email=user_in.email, limit=1)
    existing_user = existing_user_result.data[0] if existing_user_result.data else None
    if existing_user:
        logger.warning(f"[CRUD_V2] Tentative de création d'un utilisateur avec email existant: {user_in.email}")
        raise HTTPException(status_code=409, detail="Un compte avec cet email existe déjà.")

    # 2. Hacher le mot de passe (la fonction get_password_hash reste inchangée pour l'instant)
    try:
        hashed_password = get_password_hash(user_in.password)
    except ValueError as e:
        logger.error(f"[CRUD_V2] Erreur lors du hachage du mot de passe pour {user_in.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la sécurisation du mot de passe.")

    # 3. Préparer les données pour la création (exclure le mot de passe en clair)
    user_data_for_db = user_in.model_dump(exclude={"password"})
    user_data_for_db["password_hash"] = hashed_password

    # 4. Créer l'utilisateur avec FastCRUD
    try:
        # Note: crud_user.create attend un dict ou un modèle Pydantic
        #       et retourne un modèle SQLAlchemy (UserDB dans ce cas)
        created_user_db = await crud_user.create(db=db, object=user_data_for_db)
        # Le commit est géré par la dépendance get_db_session
        logger.info(f"[CRUD_V2] Utilisateur créé avec ID: {created_user_db.id} pour email: {created_user_db.email}")
        return created_user_db
    except Exception as e:
        # Le rollback est géré par la dépendance get_db_session
        logger.error(f"[CRUD_V2] Erreur lors de l'insertion de l'utilisateur {user_in.email}: {e}", exc_info=True)
        # Lever une exception pour informer l'appelant et déclencher le rollback
        raise HTTPException(status_code=500, detail="Erreur interne lors de la création de l'utilisateur.")

async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[models.UserDB]:
    """Authentifie un utilisateur par email et mot de passe en utilisant SQLAlchemy/FastCRUD."""
    logger.debug(f"[CRUD_V2] Tentative d'authentification pour: {email}")

    # 1. Récupérer l'utilisateur par email via FastCRUD (get_multi avec filtre par argument nommé)
    try:
        user_db_result = await crud_user.get_multi(db=db, email=email, limit=1)
        user_db = user_db_result.data[0] if user_db_result.data else None
    except Exception as e:
        # Gérer les erreurs potentielles lors de la récupération
        logger.error(f"[CRUD_V2] Erreur DB lors de la recherche de l'utilisateur {email}: {e}", exc_info=True)
        # Lever une exception pour rollback et erreur 500
        raise HTTPException(status_code=500, detail="Erreur interne lors de l'authentification.")

    if not user_db:
        logger.warning(f"[AUTH_V2] Utilisateur non trouvé: {email}")
        return None # Utilisateur non trouvé

    # 2. Vérifier le mot de passe (utiliser la fonction verify_password existante)
    logger.debug(f"[AUTH_V2_VERIF] Hash lu depuis DB: {user_db.password_hash}")
    logger.debug(f"[AUTH_V2_VERIF] Mot de passe reçu: '{password}'")
    if not verify_password(password, user_db.password_hash):
        logger.warning(f"[AUTH_V2] Mot de passe incorrect pour: {email}")
        return None # Mot de passe incorrect

    logger.info(f"[AUTH_V2] Authentification réussie pour: {email} (ID: {user_db.id})")
    # 3. Retourner l'objet UserDB complet (le hash sera filtré au niveau de l'API si besoin)
    return user_db

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[models.UserDB]:
    """Récupère un utilisateur par son ID en utilisant FastCRUD, chargeant éventuellement les adresses."""
    logger.debug(f"[CRUD_V2] Récupération utilisateur ID: {user_id}")
    try:
        # Utiliser eager loading pour charger les adresses en même temps si nécessaire
        # options = [selectinload(models.UserDB.addresses)]
        # user_db = await crud_user.get(db=db, id=user_id, options=options)
        user_db = await crud_user.get(db=db, id=user_id)
        if not user_db:
            logger.warning(f"[CRUD_V2] User ID {user_id} non trouvé.")
            return None # Correction de l'indentation
        return user_db
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la récupération de l'utilisateur ID {user_id}: {e}", exc_info=True)
        # Lever une exception pour rollback et erreur 500
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération de l'utilisateur.")

# ======================================================
# CRUD Operations for Addresses
# ======================================================

# --- Create Address ---
async def create_user_address(db: AsyncSession, user_id: int, address_in: models.AddressCreate) -> models.AddressDB:
    """Crée une nouvelle adresse pour un utilisateur.

    Si c'est la première adresse, elle devient l'adresse par défaut.
    Sinon, elle n'est pas par défaut.
    """
    # Vérifier si l'utilisateur existe (facultatif si la FK constraint suffit)
    user = await get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")

    # Vérifier si l'utilisateur a déjà des adresses
    existing_addresses_stmt = select(func.count(models.AddressDB.id)).where(models.AddressDB.user_id == user_id)
    address_count_result = await db.execute(existing_addresses_stmt)
    address_count = address_count_result.scalar_one()

    set_as_default = address_count == 0

    db_address = models.AddressDB(
        **address_in.model_dump(),
        user_id=user_id,
        is_default=set_as_default
    )
    db.add(db_address)
    await db.commit()
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
    """Définit une adresse comme adresse par défaut pour l'utilisateur.
    Met automatiquement les autres adresses de l'utilisateur à non-défaut.
    Lève une HTTPException 404 si l'adresse n'existe pas ou n'appartient pas à l'utilisateur.
    """
    # 1. Vérifier que l'adresse à définir existe et appartient à l'utilisateur
    address_to_set = await get_address_by_id(db, address_id_to_set)
    if not address_to_set or address_to_set.user_id != user_id:
        raise HTTPException(status_code=404, detail=f"Address with id {address_id_to_set} not found or does not belong to user {user_id}")

    # 2. Mettre toutes les adresses de l'utilisateur à is_default=False
    stmt_update_others = (
        update(models.AddressDB)
        .where(models.AddressDB.user_id == user_id)
        .values(is_default=False)
    )
    await db.execute(stmt_update_others)

    # 3. Mettre l'adresse cible à is_default=True
    address_to_set.is_default = True
    db.add(address_to_set) # Ajouter à la session pour la mise à jour

    # 4. Commiter les changements
    await db.commit()

# --- Update Address ---
async def update_user_address(
    db: AsyncSession,
    user_id: int,
    address_id: int,
    address_in: models.AddressUpdate
) -> Optional[models.AddressDB]:
    """Met à jour une adresse existante d'un utilisateur via FastCRUD."""
    logger.debug(f"[CRUD_V3] Tentative MAJ adresse ID {address_id} pour user ID {user_id} via FastCRUD")
    db_address = await get_address_by_id(db, address_id)

    # Vérifier existence et appartenance (gardé)
    if not db_address or db_address.user_id != user_id:
        logger.warning(f"[CRUD_V3] Adresse {address_id} non trouvée ou n'appartient pas à user {user_id} pour MAJ.")
        return None

    # Obtenir les données de mise à jour (exclure les non définis)
    update_data = address_in.model_dump(exclude_unset=True)

    # Si aucune donnée à mettre à jour, retourner l'adresse actuelle
    if not update_data:
        logger.debug(f"[CRUD_V3] Aucune donnée à mettre à jour pour adresse {address_id}. Retour objet actuel.")
        return db_address

    try:
        # Appliquer la mise à jour avec FastCRUD
        # Note: 'id' est utilisé par FastCRUD pour identifier l'enregistrement à mettre à jour
        updated_address_db = await crud_address.update(db=db, object=update_data, id=address_id)
        # Pas besoin de commit/refresh, géré par get_db_session et le retour de crud_address.update
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

    # Vérifier existence et appartenance (gardé)
    if not db_address or db_address.user_id != user_id:
        logger.warning(f"[CRUD_V3] Adresse {address_id} non trouvée ou n'appartient pas à user {user_id} pour suppression.")
        raise HTTPException(status_code=404, detail=f"Address with id {address_id} not found or does not belong to user {user_id}")

    # Vérifier si c'est l'adresse par défaut (gardé)
    if db_address.is_default:
        logger.warning(f"[CRUD_V3] Tentative de suppression de l'adresse par défaut {address_id} pour user {user_id}.")
        raise HTTPException(status_code=400, detail="Cannot delete the default address. Please set another address as default first.")

    # Vérifier si l'adresse est utilisée dans des commandes (gardé)
    order_check_stmt = select(func.count(models.OrderDB.id)).where(
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

    # Si tout est OK, supprimer avec FastCRUD
    try:
        # crud_address.delete attend l'ID ou l'objet à supprimer.
        # Passer l'ID est généralement plus simple si on l'a.
        await crud_address.delete(db=db, id=address_id)
        # Pas besoin de commit, géré par get_db_session.
        logger.info(f"[CRUD_V3] Adresse ID {address_id} supprimée avec succès pour user {user_id}.")
        return True
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur FastCRUD lors suppression adresse {address_id} pour user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la suppression de l'adresse.")

# --- Get Default Address --- 
async def get_default_address_for_user(db: AsyncSession, user_id: int) -> Optional[models.AddressDB]:
    """Récupère l'adresse marquée comme défaut pour un utilisateur."""
    stmt = select(models.AddressDB).where(
        and_(models.AddressDB.user_id == user_id, models.AddressDB.is_default == True)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

# ======================================================
# CRUD Operations for Categories & Tags
# ======================================================

# --- CRUD: Categories & Tags (Refactorisé) ---

async def create_category(db: AsyncSession, category_in: models.CategoryCreate) -> models.CategoryDB:
    """Crée une nouvelle catégorie en utilisant SQLAlchemy/FastCRUD."""
    logger.debug(f"[CRUD_V3] Création catégorie: {category_in.name} via FastCRUD")
    try:
        # FastCRUD gère la création
        # Attention à la contrainte UNIQUE sur 'name'
        created_category_db = await crud_category.create(db=db, object=category_in)
        # Ajout flush et refresh
        await db.flush()
        await db.refresh(created_category_db)
        logger.info(f"[CRUD_V3] Catégorie créée avec ID: {created_category_db.id}")
        return created_category_db
    except Exception as e:
        # Vérifier si l'erreur est due à la contrainte UNIQUE
        # SQLAlchemy lèvera une IntegrityError (via asyncpg)
        # Note: La détection exacte peut dépendre du driver DB et de SQLAlchemy
        if "UniqueViolationError" in str(e) or "duplicate key value violates unique constraint" in str(e):
            logger.warning(f"[CRUD_V3] Tentative de création de catégorie échouée (nom déjà existant?): {category_in.name}")
            raise HTTPException(status_code=409, detail=f"Le nom de catégorie '{category_in.name}' existe déjà.")
        else:
            logger.error(f"[CRUD_V3] Erreur inattendue lors de la création de la catégorie '{category_in.name}': {e}", exc_info=True)
            # Le rollback est géré par get_db_session
            raise HTTPException(status_code=500, detail="Erreur interne lors de la création de la catégorie.")

async def get_category(db: AsyncSession, category_id: int) -> Optional[models.CategoryDB]:
    """Récupère une catégorie par son ID en utilisant FastCRUD."""
    logger.debug(f"[CRUD_V3] Récupération catégorie ID: {category_id} via FastCRUD")
    try:
        category_db = await crud_category.get(db=db, id=category_id)
        if not category_db:
            logger.warning(f"[CRUD_V3] Catégorie ID {category_id} non trouvée.")
            return None
        return category_db
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur lors de la récupération de la catégorie ID {category_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération de la catégorie.")

async def get_all_categories(db: AsyncSession) -> List[models.CategoryDB]:
    """Récupère toutes les catégories en utilisant FastCRUD."""
    logger.debug(f"[CRUD_V3] Récupération de toutes les catégories via FastCRUD")
    try:
        # Utiliser get_multi pour récupérer toutes les catégories, triées par nom
        categories_result = await crud_category.get_multi(db=db, sort_by="name")
        logger.debug(f"[CRUD_V3] {len(categories_result.data)} catégories récupérées.")
        return categories_result.data
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur lors de la récupération de toutes les catégories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération des catégories.")

async def get_tag_by_name(db: AsyncSession, name: str) -> Optional[models.TagDB]:
    """Récupère un tag par son nom en utilisant FastCRUD."""
    logger.debug(f"[CRUD_V3] Recherche tag par nom: {name}")
    try:
        # Utiliser get_multi avec filtre par argument nommé et limite
        tag_result = await crud_tag.get_multi(db=db, name=name, limit=1)
        tag_db = tag_result.data[0] if tag_result.data else None
        return tag_db # Retourne None si non trouvé
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur lors de la recherche du tag '{name}': {e}", exc_info=True)
        # Ne pas lever d'HTTPException ici, car utilisé en interne. Laisser remonter l'erreur.
        raise # Remonter l'exception pour la gestion transactionnelle

async def create_tag(db: AsyncSession, tag_in: models.TagCreate) -> models.TagDB:
    """Crée un nouveau tag en utilisant FastCRUD. Gère l'unicité."""
    logger.debug(f"[CRUD_V3] Tentative de création tag: {tag_in.name}")
    try:
        created_tag_db = await crud_tag.create(db=db, object=tag_in)
        logger.debug(f"[CRUD_V3] Tag '{tag_in.name}' créé avec ID {created_tag_db.id}")
        return created_tag_db
    except Exception as e:
         # Vérifier si l'erreur est due à la contrainte UNIQUE
        if "UniqueViolationError" in str(e) or "duplicate key value violates unique constraint" in str(e):
            logger.warning(f"[CRUD_V3] Tentative de création du tag '{tag_in.name}' qui existe déjà.")
            # Si le tag existe déjà, on le récupère et le retourne
            existing_tag = await get_tag_by_name(db, tag_in.name)
            if existing_tag:
                return existing_tag
            else:
                # Situation anormale
                logger.error(f"[CRUD_V3] Erreur Integrity lors création tag '{tag_in.name}', mais impossible de le récupérer.")
                raise HTTPException(status_code=500, detail=f"Erreur lors de la création/récupération du tag '{tag_in.name}'.")
        else:
            logger.error(f"[CRUD_V3] Erreur inattendue lors de la création du tag '{tag_in.name}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne lors de la création du tag.")

# --- CRUD: Products & Variants (Refactorisé - Part 1) ---

async def create_product(db: AsyncSession, product_in: models.ProductCreate) -> models.ProductDB:
    """Crée un nouveau produit de base en utilisant SQLAlchemy/FastCRUD."""
    logger.debug(f"[CRUD_V3] Création du produit : {product_in.name} via FastCRUD")
    try:
        created_product_db = await crud_product.create(db=db, object=product_in)
        # Ajout flush et refresh
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
        # Charger la relation 'tags' en même temps
        options = [selectinload(models.ProductVariantDB.tags)]
        variant_db = await crud_product_variant.get(db=db, id=variant_id, options=options)
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
        # Charger la relation 'tags' en même temps
        options = [selectinload(models.ProductVariantDB.tags)]
        # Utiliser get_multi avec filtre par argument nommé et limite
        variant_result = await crud_product_variant.get_multi(
            db=db, 
            sku=sku, 
            limit=1, 
            options=options
        )
        variant_db = variant_result.data[0] if variant_result.data else None
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
        # La PK de StockDB est product_variant_id
        stock_db = await crud_stock.get(db=db, id=variant_id)
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

    # Utiliser une requête UPDATE pour la modification relative et atomique
    stmt = (
        sqlalchemy_update(models.StockDB)
        .where(models.StockDB.product_variant_id == variant_id)
        .values(
            quantity=models.StockDB.quantity + quantity_change,
            last_updated=datetime.now(datetime.timezone.utc) # Utiliser datetime.timezone.utc
            )
        .returning(models.StockDB.quantity, models.StockDB.product_variant_id) # Retourner les valeurs mises à jour
        # .execution_options(synchronize_session=False) # Optionnel
    )

    try:
        result = await db.execute(stmt)
        updated_row = result.fetchone() # Récupérer la ligne mise à jour

        if updated_row is None:
            logger.error(f"[CRUD_V2][TX] Tentative de mise à jour du stock pour variant_id {variant_id} non trouvé dans la table stock.")
            raise HTTPException(status_code=404, detail=f"Stock non trouvé pour la variation ID {variant_id}.")

        new_quantity = updated_row[0]
        product_variant_id_check = updated_row[1]

        # Vérifier si le stock est devenu négatif
        if new_quantity < 0:
            logger.error(f"[CRUD_V2][TX] Le stock pour variant_id {variant_id} deviendrait négatif ({new_quantity}). Rollback nécessaire.")
            raise ValueError("Stock insuffisant.")

        logger.debug(f"[CRUD_V2][TX] Stock mis à jour pour variant_id {variant_id}. Nouvelle quantité: {new_quantity}")

        # Re-fetch l'objet complet pour avoir l'état à jour
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

async def record_stock_movement(db: AsyncSession, movement_in: models.StockMovementCreate) -> models.StockMovementDB:
    """Enregistre un mouvement de stock."""
    logger.debug(f"[CRUD_V3][TX] Enregistrement mouvement stock: variant={movement_in.product_variant_id}, qty_change={movement_in.quantity_change}, type={movement_in.movement_type}, order_item={movement_in.order_item_id}") # Mise à jour V3
    try:
        created_movement_db = await crud_stock_movement.create(db=db, object=movement_in)
        # Ajout flush et refresh pour s'assurer que l'ID est disponible
        await db.flush()
        await db.refresh(created_movement_db)
        logger.debug(f"[CRUD_V3][TX] Mouvement de stock ID {created_movement_db.id} enregistré.") # Mise à jour V3
        return created_movement_db
    except Exception as e:
        logger.error(f"[CRUD_V3][TX] Erreur FastCRUD lors de l'enregistrement du mouvement de stock: {e}", exc_info=True) # Mise à jour V3
        # Il est important de remonter l'erreur pour que create_order puisse faire un rollback
        raise # Remonter l'exception

# --- CRUD: Quotes & Quote Items (Refactorisé) ---

async def create_quote(db: AsyncSession, user_id: int, quote_in: models.QuoteCreate) -> models.QuoteDB:
    """Crée un nouveau devis avec ses lignes, utilisant FastCRUD pour la récupération."""
    # logger.debug(f"[CRUD_V2] Création d'un devis pour user_id: {user_id} avec {len(quote_in.items)} items")
    logger.debug(f"[CRUD_V3] Création devis user {user_id} ({len(quote_in.items)} items) - Utilisation FastCRUD pour lookup variants") # Mise à jour V3

    # Vérifier que l'utilisateur existe (utilise get_user_by_id déjà refactorisé)
    user = await get_user_by_id(db, user_id)
    if not user:
        logger.warning(f"[CRUD_V3] Utilisateur {user_id} non trouvé pour création devis.")
        raise HTTPException(status_code=404, detail=f"Utilisateur ID {user_id} non trouvé.")

    # Préparer récupération des variants
    items_data_to_insert = []
    variant_ids = [item.product_variant_id for item in quote_in.items if item.product_variant_id is not None] # Exclure None au cas où
    variants_map: Dict[int, models.ProductVariantDB] = {}

    try:
        # 1. Récupérer toutes les variations nécessaires en une seule fois avec FastCRUD
        if variant_ids:
            logger.debug(f"[CRUD_V3] Récupération variants via FastCRUD: {variant_ids}")
            # Utiliser get_multi avec un filtre 'id__in'
            variants_result = await crud_product_variant.get_multi(
                db=db,
                filter={"id__in": variant_ids} # Syntaxe FastCRUD pour IN
            )
            existing_variants = variants_result.data
            variants_map = {v.id: v for v in existing_variants}
            logger.debug(f"[CRUD_V3] {len(variants_map)} variants trouvés.")

        # 2. Vérifier l'existence et préparer les données des items (inchangé)
        for item in quote_in.items:
            variant = variants_map.get(item.product_variant_id)
            if not variant:
                # logger.error(f"[CRUD_V2][TX] Variation ID {item.product_variant_id} non trouvée pour le devis.")
                logger.error(f"[CRUD_V3] Variation ID {item.product_variant_id} non trouvée dans le lookup FastCRUD.") # Mise à jour V3
                raise HTTPException(status_code=404, detail=f"Variation produit ID {item.product_variant_id} non trouvée.")
                
            items_data_to_insert.append({
                "product_variant_id": variant.id,
                "quantity": item.quantity,
                "price_at_quote": variant.price # Utiliser le prix actuel
            })

        # 3. Créer l'en-tête du devis (QuoteDB) (inchangé - gestion manuelle via SQLAlchemy)
        quote_header_data = quote_in.model_dump(exclude={'items'})
        quote_header_data['user_id'] = user_id
        new_quote_db = models.QuoteDB(**quote_header_data)

        # 4. Créer les objets QuoteItemDB et les lier au QuoteDB (inchangé)
        for item_data in items_data_to_insert:
             new_quote_db.items.append(models.QuoteItemDB(**item_data))

        # 5. Ajouter le devis (et ses items via cascade) à la session (inchangé)
        db.add(new_quote_db)
        await db.flush() 
        await db.refresh(new_quote_db, attribute_names=['items']) 

        # logger.info(f"[CRUD_V2] Devis ID {new_quote_db.id} créé avec succès pour user_id {user_id}.")
        logger.info(f"[CRUD_V3] Devis ID {new_quote_db.id} créé avec succès pour user_id {user_id}.") # Mise à jour V3
        # Le commit est géré par get_db_session

        return new_quote_db

    except HTTPException as http_exc:
         raise http_exc # Remonter les erreurs 404/409 etc.
    except Exception as e:
        # logger.error(f"[CRUD_V2] Erreur lors de la création du devis pour user {user_id}: {e}", exc_info=True)
        logger.error(f"[CRUD_V3] Erreur inattendue lors de la création du devis pour user {user_id}: {e}", exc_info=True) # Mise à jour V3
        # Le rollback est géré par get_db_session
        raise HTTPException(status_code=500, detail="Erreur interne lors de la création du devis.")

async def get_quote_by_id(db: AsyncSession, quote_id: int) -> Optional[models.QuoteDB]:
    """Récupère un devis complet par son ID, incluant utilisateur, items et variations."""
    logger.debug(f"[CRUD_V2] Récupération devis ID: {quote_id}")
    try:
        options = [
            selectinload(models.QuoteDB.user),
            selectinload(models.QuoteDB.items).selectinload(models.QuoteItemDB.variant).selectinload(models.ProductVariantDB.tags) # Charger items -> variant -> tags
        ]
        # Utiliser crud_quote.get avec les options de chargement
        quote_db = await crud_quote.get(db=db, id=quote_id, options=options)

        if not quote_db:
            logger.warning(f"[CRUD_V2] Devis ID {quote_id} non trouvé.")
            return None # Correction de l'indentation

        logger.debug(f"[CRUD_V2] Devis ID {quote_id} récupéré avec {len(quote_db.items)} lignes.")
        return quote_db

    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la récupération du devis ID {quote_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération du devis.")

async def list_user_quotes(db: AsyncSession, user_id: int, limit: int = 20, offset: int = 0) -> List[models.QuoteDB]:
    """Liste les devis pour un utilisateur donné (en-têtes seulement)."""
    logger.debug(f"[CRUD_V2] Listage des devis pour user_id: {user_id} (limit={limit}, offset={offset})")
    try:
        # Utiliser crud_quote.get_multi avec filtre et pagination
        # Ne pas charger les items pour la liste par défaut
        quotes_result = await crud_quote.get_multi(
            db=db,
            offset=offset,
            limit=limit,
            filter={"user_id": user_id},
            sort_by="-quote_date" # Trier par date la plus récente
        )
        logger.debug(f"[CRUD_V2] {len(quotes_result.data)} devis récupérés pour user_id {user_id}.")
        return quotes_result.data
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors du listage des devis pour user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors du listage des devis.")

async def update_quote_status(db: AsyncSession, quote_id: int, status: str) -> models.QuoteDB:
    """Met à jour le statut d'un devis."""
    logger.debug(f"[CRUD_V3] Mise à jour statut devis ID: {quote_id} -> {status}")
    allowed_statuses = ['pending', 'accepted', 'rejected', 'expired'] # Exemple
    if status not in allowed_statuses:
        logger.error(f"[CRUD_V3] Statut invalide '{status}' pour mise à jour devis.")
        raise HTTPException(status_code=400, detail=f"Statut invalide. Doit être l'un de: {', '.join(allowed_statuses)}")

    try:
        # Utiliser une requête update directe est plus simple ici.
        stmt = (
            sqlalchemy_update(models.QuoteDB)
            .where(models.QuoteDB.id == quote_id)
            .values(status=status, updated_at=datetime.now(datetime.timezone.utc)) # Utiliser datetime.timezone.utc
            # .execution_options(synchronize_session=False)
            .returning(models.QuoteDB.id) # Vérifier que l'update a eu lieu
        )
        result = await db.execute(stmt)
        updated_id = result.scalar_one_or_none()

        if updated_id is None:
            logger.warning(f"[CRUD_V3] Devis ID {quote_id} non trouvé pour mise à jour statut.")
            raise HTTPException(status_code=404, detail=f"Devis ID {quote_id} non trouvé.")

        # Le commit est géré par get_db_session
        logger.info(f"[CRUD_V3] Statut du devis ID {quote_id} mis à jour à '{status}'.")

        # Recharger le devis pour retourner l'état complet mis à jour
        updated_quote = await get_quote_by_id(db, quote_id)
        if not updated_quote: # Ne devrait pas arriver
            raise HTTPException(status_code=500, detail="Erreur interne: Impossible de récupérer le devis après mise à jour.")
        return updated_quote

    except HTTPException as http_exc:
         raise http_exc # Remonter 400 ou 404
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur lors de la mise à jour du statut du devis {quote_id}: {e}", exc_info=True)
        # Le rollback est géré par get_db_session
        raise HTTPException(status_code=500, detail="Erreur interne lors de la mise à jour du statut du devis.")

# --- CRUD: Orders & Order Items (Refactorisé) ---

async def create_order(db: AsyncSession, user_id: int, order_in: models.OrderCreate) -> models.OrderDB:
    """Crée une nouvelle commande, met à jour le stock et enregistre les mouvements."""
    # logger.debug(f"[CRUD_V2] Création de commande pour user_id: {user_id} avec {len(order_in.items)} items")
    logger.debug(f"[CRUD_V3][TX] Démarrage création commande pour user_id: {user_id} ({len(order_in.items)} items)")

    # 1. Vérifier existence utilisateur et adresses via FastCRUD / helpers
    user = await get_user_by_id(db, user_id) # Utilise déjà FastCRUD get
    if not user:
        logger.warning(f"[CRUD_V3][TX] Utilisateur ID {user_id} non trouvé.")
        raise HTTPException(status_code=404, detail=f"Utilisateur ID {user_id} non trouvé.")

    # Utiliser get_address_by_id (qui utilise db.get, équivalent à crud_address.get)
    delivery_address = await get_address_by_id(db, order_in.delivery_address_id)
    if not delivery_address or delivery_address.user_id != user_id:
        logger.warning(f"[CRUD_V3][TX] Adresse livraison ID {order_in.delivery_address_id} invalide pour user {user_id}.")
        raise HTTPException(status_code=404, detail=f"Adresse de livraison ID {order_in.delivery_address_id} invalide.")
    billing_address = await get_address_by_id(db, order_in.billing_address_id)
    if not billing_address or billing_address.user_id != user_id:
        logger.warning(f"[CRUD_V3][TX] Adresse facturation ID {order_in.billing_address_id} invalide pour user {user_id}.")
        raise HTTPException(status_code=404, detail=f"Adresse de facturation ID {order_in.billing_address_id} invalide.")

    items_data_to_process = []
    variant_ids = [item.product_variant_id for item in order_in.items if item.product_variant_id is not None]
    variants_map: Dict[int, models.ProductVariantDB] = {}
    calculated_total = Decimal(0)

    try:
        # 2. Récupérer variations via FastCRUD et vérifier stock
        if variant_ids:
            logger.debug(f"[CRUD_V3][TX] Récupération variants via FastCRUD: {variant_ids}")
            variants_result = await crud_product_variant.get_multi(
                db=db,
                filter={"id__in": variant_ids}
            )
            existing_variants = variants_result.data
            variants_map = {v.id: v for v in existing_variants}
            logger.debug(f"[CRUD_V3][TX] {len(variants_map)} variants trouvés.")

        for item in order_in.items:
            variant = variants_map.get(item.product_variant_id)
            if not variant:
                 logger.error(f"[CRUD_V3][TX] Variation ID {item.product_variant_id} non trouvée dans lookup FastCRUD.")
                 raise HTTPException(status_code=404, detail=f"Variation produit ID {item.product_variant_id} non trouvée.")
            
            # Vérification du stock (inchangé - utilise get_stock_for_variant)
            stock_info = await get_stock_for_variant(db, variant.id)
            current_stock = stock_info.quantity if stock_info else 0
            if current_stock < item.quantity:
                 logger.warning(f"[CRUD_V3][TX] Stock insuffisant (pré-vérif) pour variant_id {variant.id} (demandé: {item.quantity}, dispo: {current_stock})")
                 raise HTTPException(status_code=409, detail=f"Stock insuffisant pour le produit SKU {variant.sku}. Disponible: {current_stock}")

            price = variant.price
            items_data_to_process.append({
                "variant_id": variant.id,
                "sku": variant.sku, # Ajouter SKU pour log
                "quantity": item.quantity,
                "price_at_order": price
            })
            calculated_total += (price * item.quantity)
        
        # Vérifier total (inchangé)
        if calculated_total != order_in.total_amount:
             logger.warning(f"[CRUD_V3][TX] Incohérence de montant total (calculé: {calculated_total}, fourni: {order_in.total_amount}) - Utilisation du montant calculé.")
             final_total_amount = calculated_total
        else:
             final_total_amount = order_in.total_amount
        
        logger.debug(f"[CRUD_V3][TX] Vérifications OK. Total: {final_total_amount}. Création commande...")

        # 3. Créer l'en-tête de commande (inchangé - SQLAlchemy manuel)
        order_header_data = order_in.model_dump(exclude={'items'})
        order_header_data['user_id'] = user_id
        order_header_data['total_amount'] = final_total_amount
        new_order_db = models.OrderDB(**order_header_data)
        db.add(new_order_db)
        await db.flush() # Obtenir l'ID de la commande
        logger.debug(f"[CRUD_V3][TX] En-tête commande ID {new_order_db.id} créé (flush). Création items...")

        # 4. Créer OrderItems, MAJ Stock, créer StockMovements (logique inchangée)
        # created_order_items_db = [] # Liste non utilisée, on peut simplifier
        for item_data in items_data_to_process:
            logger.debug(f"[CRUD_V3][TX] Traitement item: variant={item_data['variant_id']}, qty={item_data['quantity']}")
            # 4a. Créer Order Item (SQLAlchemy manuel)
            order_item_db = models.OrderItemDB(
                order_id=new_order_db.id,
                product_variant_id=item_data["variant_id"],
                quantity=item_data["quantity"],
                price_at_order=item_data["price_at_order"]
            )
            db.add(order_item_db)
            await db.flush() # Obtenir l'ID de l'order item
            # created_order_items_db.append(order_item_db)
            logger.debug(f"[CRUD_V3][TX] OrderItem ID {order_item_db.id} créé (flush). Mise à jour stock...")

            # 4b. Mettre à jour le stock (inchangé - utilise update_stock_for_variant)
            try:
                 # update_stock_for_variant lève ValueError puis HTTPException(409) si stock insuffisant
                 await update_stock_for_variant(db, item_data["variant_id"], -item_data["quantity"])
                 logger.debug(f"[CRUD_V3][TX] Stock mis à jour pour variant {item_data['variant_id']}. Enregistrement mouvement...")
            except HTTPException as stock_error:
                 # Remonter l'erreur pour rollback global
                 logger.error(f"[CRUD_V3][TX] Échec MAJ stock (HTTPException) pour variant {item_data['variant_id']}: {stock_error.detail}")
                 raise stock_error
            except ValueError as stock_error_val: # Capturer ValueError aussi
                 logger.error(f"[CRUD_V3][TX] Échec MAJ stock (ValueError) pour variant {item_data['variant_id']}: {stock_error_val}")
                 raise HTTPException(status_code=409, detail=str(stock_error_val)) # Transformer en HTTPException
                 
            # 4c. Enregistrer le mouvement de stock (utilise record_stock_movement refactorisé)
            movement_data = models.StockMovementCreate(
                product_variant_id=item_data["variant_id"],
                quantity_change=-item_data["quantity"],
                movement_type='order_fulfillment',
                order_item_id=order_item_db.id # Lier au OrderItem créé
            )
            await record_stock_movement(db, movement_data)
            logger.debug(f"[CRUD_V3][TX] Mouvement stock enregistré pour OrderItem {order_item_db.id}.")

        # 5. Rafraîchir la commande complète (inchangé)
        logger.debug(f"[CRUD_V3][TX] Tous items traités. Refresh commande ID {new_order_db.id}...")
        await db.refresh(new_order_db, attribute_names=['items', 'user', 'delivery_address', 'billing_address'])

        logger.info(f"[CRUD_V3][TX] Commande ID {new_order_db.id} créée avec succès pour user_id {user_id}.")
        # Le commit sera fait par get_db_session si aucune exception n'est levée

        return new_order_db

    except HTTPException as http_exc:
         logger.warning(f"[CRUD_V3][TX] HTTP Exception durant création commande: {http_exc.status_code} - {http_exc.detail}")
         # Le rollback sera fait par get_db_session
         raise http_exc
    except Exception as e:
        logger.error(f"[CRUD_V3][TX] Erreur inattendue pendant création commande pour user {user_id}: {e}", exc_info=True)
        # Le rollback sera fait par get_db_session
        raise HTTPException(status_code=500, detail="Erreur interne lors de la création de la commande.")

async def get_order_by_id(db: AsyncSession, order_id: int) -> Optional[models.OrderDB]:
    """Récupère une commande complète par son ID."""
    logger.debug(f"[CRUD_V2] Récupération commande ID: {order_id}")
    try:
        options = [
            selectinload(models.OrderDB.user),
            selectinload(models.OrderDB.delivery_address),
            selectinload(models.OrderDB.billing_address),
            selectinload(models.OrderDB.items).selectinload(models.OrderItemDB.variant).selectinload(models.ProductVariantDB.tags)
        ]
        order_db = await crud_order.get(db=db, id=order_id, options=options)

        if not order_db:
            logger.warning(f"[CRUD_V2] Commande ID {order_id} non trouvée.")
            return None
                
        logger.debug(f"[CRUD_V2] Commande ID {order_id} récupérée avec {len(order_db.items)} lignes.")
        return order_db

    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la récupération de la commande ID {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération de la commande.")

async def list_user_orders(db: AsyncSession, user_id: int, limit: int = 20, offset: int = 0) -> List[models.OrderDB]:
    """Liste les commandes pour un utilisateur donné (en-têtes seulement)."""
    logger.debug(f"[CRUD_V2] Listage des commandes pour user_id: {user_id} (limit={limit}, offset={offset})")
    try:
        orders_result = await crud_order.get_multi(
            db=db,
            offset=offset,
            limit=limit,
            filter={"user_id": user_id},
            sort_by="-order_date"
        )
        logger.debug(f"[CRUD_V2] {len(orders_result.data)} commandes récupérées pour user_id {user_id}.")
        return orders_result.data
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors du listage des commandes pour user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors du listage des commandes.")

async def update_order_status(db: AsyncSession, order_id: int, status: str) -> models.OrderDB:
    """Met à jour le statut d'une commande."""
    logger.debug(f"[CRUD_V3] Mise à jour statut commande ID: {order_id} -> {status}")
    allowed_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled'] 
    if status not in allowed_statuses:
        logger.error(f"[CRUD_V3] Statut invalide '{status}' pour mise à jour commande.")
        raise HTTPException(status_code=400, detail=f"Statut invalide. Doit être l'un de: {', '.join(allowed_statuses)}")

    try:
        stmt = (
            sqlalchemy_update(models.OrderDB)
            .where(models.OrderDB.id == order_id)
            .values(status=status, updated_at=datetime.now(datetime.timezone.utc)) # Utiliser datetime.timezone.utc
            .returning(models.OrderDB.id)
        )
        result = await db.execute(stmt)
        updated_id = result.scalar_one_or_none()

        if updated_id is None:
            logger.warning(f"[CRUD_V3] Commande ID {order_id} non trouvée pour mise à jour statut.")
            raise HTTPException(status_code=404, detail=f"Commande ID {order_id} non trouvée.")
                
        logger.info(f"[CRUD_V3] Statut de la commande ID {order_id} mis à jour à '{status}'.")

        # Recharger la commande pour retourner l'état complet
        updated_order = await get_order_by_id(db, order_id)
        if not updated_order:
            raise HTTPException(status_code=500, detail="Erreur interne: Impossible de récupérer la commande après mise à jour.")
        return updated_order

    except HTTPException as http_exc:
         raise http_exc
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur lors de la mise à jour du statut de la commande {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la mise à jour du statut de la commande.")

# --- Fonctions pour list_products (avec jointures/filtres complexes) --- 

# Note: Ces fonctions restent en SQLAlchemy "manuel" car les filtres 
# (tags many-to-many, search multi-tables) sont trop complexes pour le 
# système de filtre standard de FastCRUD.

async def _build_product_list_query(
    db: AsyncSession, 
    category_id: Optional[int] = None, 
    tag_names: Optional[List[str]] = None,
    search_term: Optional[str] = None
):
    """Helper pour construire la requête de base (select + joins + filters)."""
    # Sélectionne le produit principal
    stmt = future_select(models.ProductDB)
    
    # Joindre systématiquement avec les variations car on en a besoin pour les filtres/infos
    stmt = stmt.join(models.ProductDB.variants)
    
    # Filtrer par catégorie si fournie
    if category_id is not None:
        stmt = stmt.where(models.ProductDB.category_id == category_id)
        
    # Filtrer par tags si fournis (jointure et filtre ANY)
    if tag_names:
        # Joindre avec la table d'association et les tags
        stmt = stmt.join(models.ProductVariantDB.tags)
        # Filtrer où le nom du tag est dans la liste fournie
        stmt = stmt.where(models.TagDB.name.in_(tag_names))
        
    # Filtrer par terme de recherche (ILIKE sur plusieurs champs)
    if search_term:
        search_pattern = f"%{search_term}%"
        stmt = stmt.where(
            or_(
                models.ProductDB.name.ilike(search_pattern),
                models.ProductDB.description.ilike(search_pattern),
                models.ProductVariantDB.sku.ilike(search_pattern),
                # Ajouter la recherche sur variant.attribute_description si ce champ existe
                # cast(models.ProductVariantDB.attributes ->> 'description', SQLString).ilike(search_pattern) # Exemple pour JSONB
            )
        )
        
    # Assurer qu'on retourne des produits distincts
    stmt = stmt.distinct()
    
    return stmt

async def count_products_with_variants(
    db: AsyncSession, 
    category_id: Optional[int] = None, 
    tag_names: Optional[List[str]] = None,
    search_term: Optional[str] = None
) -> int:
    """Compte les produits correspondant aux filtres."""
    logger.debug(f"[CRUD_V3] Comptage produits avec filtres: cat={category_id}, tags={tag_names}, search={search_term}")
    try:
        # Construire la requête de base avec filtres
        base_query = await _build_product_list_query(
            db=db, 
            category_id=category_id, 
            tag_names=tag_names,
            search_term=search_term
        )
        
        # Transformer la requête pour compter les ID uniques de ProductDB
        count_query = future_select(sql_func.count(distinct(models.ProductDB.id)))
        count_query = count_query.select_from(base_query.subquery()) # Appliquer les filtres en comptant depuis la sous-requête
        
        # Exécuter la requête de comptage
        result = await db.execute(count_query)
        total_count = result.scalar_one_or_none() or 0
        logger.debug(f"[CRUD_V3] Total produits trouvés: {total_count}")
        return total_count
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur lors du comptage des produits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors du comptage des produits.")

async def list_products_with_variants(
    db: AsyncSession, 
    limit: int = 100, 
    offset: int = 0, 
    category_id: Optional[int] = None, 
    tag_names: Optional[List[str]] = None, 
    search_term: Optional[str] = None
) -> List[models.ProductDB]:
    """Liste les produits avec variations, appliquant filtres et pagination."""
    logger.debug(f"[CRUD_V3] Listage produits avec filtres: cat={category_id}, tags={tag_names}, search={search_term}, limit={limit}, offset={offset}")
    try:
        # Construire la requête de base avec filtres
        stmt = await _build_product_list_query(
            db=db, 
            category_id=category_id, 
            tag_names=tag_names,
            search_term=search_term
        )
        
        # Ajouter le chargement Eager des variations et de leurs tags
        stmt = stmt.options(
            selectinload(models.ProductDB.variants).selectinload(models.ProductVariantDB.tags)
        )
        
        # Ajouter l'ordre (important pour une pagination cohérente)
        stmt = stmt.order_by(models.ProductDB.id) # Ou un autre champ pertinent
        
        # Appliquer la pagination
        stmt = stmt.offset(offset).limit(limit)
        
        # Exécuter la requête
        result = await db.execute(stmt)
        # .unique() est important après distinct() + selectinload pour éviter les doublons en mémoire dus aux jointures
        products_db = list(result.unique().scalars().all())
        
        logger.debug(f"[CRUD_V3] {len(products_db)} produits récupérés pour la page.")
        return products_db
    except Exception as e:
        logger.error(f"[CRUD_V3] Erreur lors du listage des produits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors du listage des produits.")
