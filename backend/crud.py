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
import timezone
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

crud_user = FastCRUD(UserDB, UserCreate, User, User) # TODO: Créer UserUpdate si besoin
crud_address = FastCRUD(AddressDB, AddressCreate, Address, Address) # TODO: Créer AddressUpdate
crud_category = FastCRUD(CategoryDB, CategoryCreate, Category, Category) # TODO: Créer CategoryUpdate
crud_tag = FastCRUD(TagDB, TagCreate, Tag, Tag) # TODO: Créer TagUpdate
crud_product = FastCRUD(ProductDB, ProductCreate, Product, Product) # TODO: Créer ProductUpdate
crud_product_variant = FastCRUD(ProductVariantDB, ProductVariantCreate, ProductVariant, ProductVariant) # TODO: Créer ProductVariantUpdate
crud_stock = FastCRUD(StockDB, models.Stock, models.Stock, models.Stock) # TODO: Affiner schémas Stock si besoin
crud_stock_movement = FastCRUD(StockMovementDB, StockMovementCreate, StockMovement, StockMovement)
crud_quote = FastCRUD(QuoteDB, QuoteCreate, Quote, Quote) # TODO: Créer QuoteUpdate
crud_quote_item = FastCRUD(QuoteItemDB, QuoteItemCreate, QuoteItem, QuoteItem)
crud_order = FastCRUD(OrderDB, OrderCreate, Order, Order) # TODO: Créer OrderUpdate
crud_order_item = FastCRUD(OrderItemDB, OrderItemCreate, OrderItem, OrderItem)

# ======================================================
# Logique CRUD (Avec SQLAlchemy & FastCRUD - Nouvelle)
# ======================================================

# --- CRUD: Users & Authentication (Refactorisé) ---

async def create_user(db: AsyncSession, user_in: models.UserCreate) -> models.UserDB:
    """Crée un nouvel utilisateur en utilisant SQLAlchemy et FastCRUD."""
    logger.debug(f"[CRUD_V2] Création utilisateur: {user_in.email}")

    # 1. Vérifier si l'email existe déjà en utilisant FastCRUD
    existing_user = await crud_user.get_by_field(db=db, field="email", value=user_in.email)
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

# La fonction authenticate_user nécessite également une refactorisation similaire
async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[models.UserDB]:
    """Authentifie un utilisateur par email et mot de passe en utilisant SQLAlchemy/FastCRUD."""
    logger.debug(f"[CRUD_V2] Tentative d'authentification pour: {email}")

    # 1. Récupérer l'utilisateur par email via FastCRUD
    #    Note: S'assure que le modèle UserDB charge bien le password_hash.
    try:
        user_db = await crud_user.get_by_field(db=db, field="email", value=email)
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

def authenticate_user_old(email: str, password: str) -> Optional[models.User]:
    """(Ancien - psycopg2) Authentifie un utilisateur par email et mot de passe."""
    logger.debug(f"[CRUD_OLD] Tentative d'authentification pour: {email}")
    # ... existing code ...

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
            return None
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
    """Met à jour une adresse existante d'un utilisateur.

    Ne permet pas de changer user_id ou is_default via cet appel.
    Retourne l'adresse mise à jour ou None si non trouvée / n'appartient pas à l'user.
    """
    db_address = await get_address_by_id(db, address_id)

    # Vérifier existence et appartenance
    if not db_address or db_address.user_id != user_id:
        return None

    # Obtenir les données de mise à jour (exclure les non définis)
    update_data = address_in.model_dump(exclude_unset=True)

    # Si aucune donnée à mettre à jour, retourner l'adresse actuelle
    if not update_data:
        return db_address

    # Appliquer les mises à jour
    for key, value in update_data.items():
        setattr(db_address, key, value)

    db.add(db_address)
    await db.commit()
    await db.refresh(db_address)

    return db_address

# --- Delete Address ---
async def delete_user_address(db: AsyncSession, user_id: int, address_id: int) -> bool:
    """Supprime une adresse d'un utilisateur.

    Vérifie l'appartenance, si l'adresse est par défaut, ou si elle est utilisée dans des commandes.
    Retourne True si supprimée, False sinon (ou lève une exception).
    Lève HTTPException 400 si la suppression est interdite (défaut, utilisée).
    Lève HTTPException 404 si non trouvée / n'appartient pas à l'user.
    """
    db_address = await get_address_by_id(db, address_id)

    # Vérifier existence et appartenance
    if not db_address or db_address.user_id != user_id:
        raise HTTPException(status_code=404, detail=f"Address with id {address_id} not found or does not belong to user {user_id}")

    # Vérifier si c'est l'adresse par défaut
    if db_address.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete the default address. Please set another address as default first.")

    # Vérifier si l'adresse est utilisée dans des commandes (RESTRICT serait levé par DB, mais pré-vérifions)
    # Utiliser select(func.count()) pour être efficace
    order_check_stmt = select(func.count(models.OrderDB.id)).where(
        or_(
            models.OrderDB.delivery_address_id == address_id,
            models.OrderDB.billing_address_id == address_id
        )
    )
    order_count_result = await db.execute(order_check_stmt)
    order_count = order_count_result.scalar_one()

    if order_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete address with id {address_id} as it is used in {order_count} existing order(s).")

    # Si tout est OK, supprimer
    await db.delete(db_address)
    await db.commit()
    return True

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
    logger.debug(f"[CRUD_V2] Création catégorie: {category_in.name}")
    try:
        # FastCRUD gère la création
        # Attention à la contrainte UNIQUE sur 'name'
        created_category_db = await crud_category.create(db=db, object=category_in)
        # Le commit est géré par get_db_session
        logger.info(f"[CRUD_V2] Catégorie créée avec ID: {created_category_db.id}")
        return created_category_db
    except Exception as e:
        # Vérifier si l'erreur est due à la contrainte UNIQUE
        # SQLAlchemy lèvera une IntegrityError (via asyncpg)
        # Note: La détection exacte peut dépendre du driver DB et de SQLAlchemy
        if "UniqueViolationError" in str(e) or "duplicate key value violates unique constraint" in str(e):
             logger.warning(f"[CRUD_V2] Tentative de création de catégorie échouée (nom déjà existant?): {category_in.name}")
             raise HTTPException(status_code=409, detail=f"Le nom de catégorie '{category_in.name}' existe déjà.")
        else:
             logger.error(f"[CRUD_V2] Erreur inattendue lors de la création de la catégorie '{category_in.name}': {e}", exc_info=True)
             # Le rollback est géré par get_db_session
             raise HTTPException(status_code=500, detail="Erreur interne lors de la création de la catégorie.")

async def get_category(db: AsyncSession, category_id: int) -> Optional[models.CategoryDB]:
    """Récupère une catégorie par son ID en utilisant FastCRUD."""
    logger.debug(f"[CRUD_V2] Récupération catégorie ID: {category_id}")
    try:
        category_db = await crud_category.get(db=db, id=category_id)
        if not category_db:
            logger.warning(f"[CRUD_V2] Catégorie ID {category_id} non trouvée.")
            return None
        return category_db
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la récupération de la catégorie ID {category_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération de la catégorie.")

async def get_all_categories(db: AsyncSession) -> List[models.CategoryDB]:
    """Récupère toutes les catégories en utilisant FastCRUD."""
    logger.debug(f"[CRUD_V2] Récupération de toutes les catégories")
    try:
        # Utiliser get_multi pour récupérer toutes les catégories, triées par nom
        categories_result = await crud_category.get_multi(db=db, sort_by="name")
        logger.debug(f"[CRUD_V2] {len(categories_result.data)} catégories récupérées.")
        return categories_result.data
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la récupération de toutes les catégories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération des catégories.")

async def get_tag_by_name(db: AsyncSession, name: str) -> Optional[models.TagDB]:
    """Récupère un tag par son nom en utilisant FastCRUD."""
    logger.debug(f"[CRUD_V2] Recherche tag par nom: {name}")
    try:
        tag_db = await crud_tag.get_by_field(db=db, field="name", value=name)
        return tag_db # Retourne None si non trouvé
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la recherche du tag '{name}': {e}", exc_info=True)
        # Ne pas lever d'HTTPException ici, car utilisé en interne. Laisser remonter l'erreur.
        raise

async def create_tag(db: AsyncSession, tag_in: models.TagCreate) -> models.TagDB:
    """Crée un nouveau tag en utilisant FastCRUD. Gère l'unicité."""
    logger.debug(f"[CRUD_V2] Tentative de création tag: {tag_in.name}")
    try:
        created_tag_db = await crud_tag.create(db=db, object=tag_in)
        logger.debug(f"[CRUD_V2] Tag '{tag_in.name}' créé avec ID {created_tag_db.id}")
        return created_tag_db
    except Exception as e:
         # Vérifier si l'erreur est due à la contrainte UNIQUE
        if "UniqueViolationError" in str(e) or "duplicate key value violates unique constraint" in str(e):
             logger.warning(f"[CRUD_V2] Tentative de création du tag '{tag_in.name}' qui existe déjà.")
             # Si le tag existe déjà, on le récupère et le retourne
             existing_tag = await get_tag_by_name(db, tag_in.name)
             if existing_tag:
                 return existing_tag
             else:
                 # Situation anormale
                 logger.error(f"[CRUD_V2] Erreur Integrity lors création tag '{tag_in.name}', mais impossible de le récupérer.")
                 raise HTTPException(status_code=500, detail=f"Erreur lors de la création/récupération du tag '{tag_in.name}'.")
        else:
            logger.error(f"[CRUD_V2] Erreur inattendue lors de la création du tag '{tag_in.name}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne lors de la création du tag.")

# --- CRUD: Products & Variants (Refactorisé - Part 1) ---

async def create_product(db: AsyncSession, product_in: models.ProductCreate) -> models.ProductDB:
    """Crée un nouveau produit de base en utilisant SQLAlchemy/FastCRUD."""
    logger.debug(f"[CRUD_V2] Création du produit : {product_in.name}")
    try:
        created_product_db = await crud_product.create(db=db, object=product_in)
        logger.info(f"[CRUD_V2] Produit créé avec ID: {created_product_db.id}")
        return created_product_db
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la création du produit '{product_in.name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la création du produit.")

async def get_product_variant_by_id(db: AsyncSession, variant_id: int) -> Optional[models.ProductVariantDB]:
    """Récupère une variation par son ID, incluant ses tags (eager loading)."""
    logger.debug(f"[CRUD_V2] Récupération variant ID {variant_id} avec tags")
    try:
        # Charger la relation 'tags' en même temps
        options = [selectinload(models.ProductVariantDB.tags)]
        variant_db = await crud_product_variant.get(db=db, id=variant_id, options=options)
        if not variant_db:
            logger.warning(f"[CRUD_V2] Variation ID {variant_id} non trouvée.")
            return None
        return variant_db
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur récupération variant ID {variant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération de la variation.")

async def get_product_variant_by_sku(db: AsyncSession, sku: str) -> Optional[models.ProductVariantDB]:
    """Récupère une variation de produit par son SKU, incluant ses tags (eager loading)."""
    logger.debug(f"[CRUD_V2] Recherche de la variation SKU: {sku} avec tags")
    try:
        # Charger la relation 'tags' en même temps
        options = [selectinload(models.ProductVariantDB.tags)]
        variant_db = await crud_product_variant.get_by_field(db=db, field="sku", value=sku, options=options)
        if not variant_db:
            logger.warning(f"[CRUD_V2] Variation SKU {sku} non trouvée.")
            return None
        return variant_db
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la recherche de la variation SKU {sku}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération de la variation.")

# --- CRUD: Stock & Movements (Refactorisé) ---

async def get_stock_for_variant(db: AsyncSession, variant_id: int) -> Optional[models.StockDB]:
    """Récupère l'objet StockDB pour une variation donnée."""
    logger.debug(f"[CRUD_V2] Vérification du stock pour variant_id: {variant_id}")
    try:
        # La PK de StockDB est product_variant_id
        stock_db = await crud_stock.get(db=db, id=variant_id)
        # crud_stock.get retourne None si non trouvé
        if not stock_db:
             logger.warning(f"[CRUD_V2] Enregistrement de stock non trouvé pour variant_id {variant_id}")
             return None
        logger.debug(f"[CRUD_V2] Stock trouvé pour variant_id {variant_id}: qte={stock_db.quantity}")
        return stock_db
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la récupération du stock pour variant {variant_id}: {e}", exc_info=True)
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
            last_updated=datetime.now(timezone.utc) # Assurer la timezone UTC
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
    logger.debug(f"[CRUD_V2][TX] Enregistrement mouvement stock pour variant_id {movement_in.product_variant_id}, qte: {movement_in.quantity_change}, type: {movement_in.movement_type}")
    try:
        created_movement_db = await crud_stock_movement.create(db=db, object=movement_in)
        logger.debug("[CRUD_V2][TX] Mouvement de stock enregistré.")
        return created_movement_db
    except Exception as e:
        logger.error(f"[CRUD_V2][TX] Erreur lors de l'enregistrement du mouvement de stock: {e}", exc_info=True)
        raise

# --- CRUD: Quotes & Quote Items (Refactorisé) ---

async def create_quote(db: AsyncSession, user_id: int, quote_in: models.QuoteCreate) -> models.QuoteDB:
    """Crée un nouveau devis avec ses lignes."""
    logger.debug(f"[CRUD_V2] Création d'un devis pour user_id: {user_id} avec {len(quote_in.items)} items")

    # Vérifier que l'utilisateur existe
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Utilisateur ID {user_id} non trouvé.")

    items_data_to_insert = []
    variant_ids = [item.product_variant_id for item in quote_in.items]
    variants_map: Dict[int, models.ProductVariantDB] = {}

    try:
        # 1. Récupérer toutes les variations nécessaires en une seule fois
        if variant_ids:
            stmt = select(models.ProductVariantDB).where(models.ProductVariantDB.id.in_(variant_ids))
            result = await db.execute(stmt)
            existing_variants = result.scalars().all()
            variants_map = {v.id: v for v in existing_variants}

        # 2. Vérifier l'existence et préparer les données des items
        for item in quote_in.items:
            variant = variants_map.get(item.product_variant_id)
            if not variant:
                logger.error(f"[CRUD_V2][TX] Variation ID {item.product_variant_id} non trouvée pour le devis.")
                raise HTTPException(status_code=404, detail=f"Variation produit ID {item.product_variant_id} non trouvée.")

            items_data_to_insert.append({
                "product_variant_id": variant.id,
                "quantity": item.quantity,
                "price_at_quote": variant.price # Utiliser le prix actuel
            })

        # 3. Créer l'en-tête du devis (QuoteDB)
        # Préparer les données, exclure 'items' du modèle Pydantic
        quote_header_data = quote_in.model_dump(exclude={'items'})
        quote_header_data['user_id'] = user_id # Assurer que user_id est inclus
        new_quote_db = models.QuoteDB(**quote_header_data)

        # 4. Créer les objets QuoteItemDB et les lier au QuoteDB
        for item_data in items_data_to_insert:
             new_quote_db.items.append(models.QuoteItemDB(**item_data))
             # La relation back_populates devrait lier item.quote = new_quote_db

        # 5. Ajouter le devis (et ses items via cascade) à la session
        db.add(new_quote_db)
        await db.flush() # Pour obtenir l'ID du devis et des items si nécessaire
        await db.refresh(new_quote_db, attribute_names=['items']) # Rafraîchir pour charger les items liés

        logger.info(f"[CRUD_V2] Devis ID {new_quote_db.id} créé avec succès pour user_id {user_id}.")
        # Le commit est géré par get_db_session

        return new_quote_db

    except HTTPException as http_exc:
         raise http_exc # Remonter les erreurs 404
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la création du devis pour user {user_id}: {e}", exc_info=True)
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
            return None

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
    logger.debug(f"[CRUD_V2] Mise à jour statut devis ID: {quote_id} -> {status}")
    allowed_statuses = ['pending', 'accepted', 'rejected', 'expired'] # Exemple
    if status not in allowed_statuses:
        logger.error(f"[CRUD_V2] Statut invalide '{status}' pour mise à jour devis.")
        raise HTTPException(status_code=400, detail=f"Statut invalide. Doit être l'un de: {', '.join(allowed_statuses)}")

    try:
        # Utiliser une requête update directe est plus simple ici.
        stmt = (
            sqlalchemy_update(models.QuoteDB)
            .where(models.QuoteDB.id == quote_id)
            .values(status=status, updated_at=datetime.now(timezone.utc))
            # .execution_options(synchronize_session=False)
            .returning(models.QuoteDB.id) # Vérifier que l'update a eu lieu
        )
        result = await db.execute(stmt)
        updated_id = result.scalar_one_or_none()

        if updated_id is None:
            logger.warning(f"[CRUD_V2] Devis ID {quote_id} non trouvé pour mise à jour statut.")
            raise HTTPException(status_code=404, detail=f"Devis ID {quote_id} non trouvé.")

        # Le commit est géré par get_db_session
        logger.info(f"[CRUD_V2] Statut du devis ID {quote_id} mis à jour à '{status}'.")

        # Recharger le devis pour retourner l'état complet mis à jour
        updated_quote = await get_quote_by_id(db, quote_id)
        if not updated_quote: # Ne devrait pas arriver
             raise HTTPException(status_code=500, detail="Erreur interne: Impossible de récupérer le devis après mise à jour.")
        return updated_quote

    except HTTPException as http_exc:
         raise http_exc # Remonter 400 ou 404
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la mise à jour du statut du devis {quote_id}: {e}", exc_info=True)
        # Le rollback est géré par get_db_session
        raise HTTPException(status_code=500, detail="Erreur interne lors de la mise à jour du statut du devis.")

# --- CRUD: Orders & Order Items (Refactorisé) ---

async def create_order(db: AsyncSession, user_id: int, order_in: models.OrderCreate) -> models.OrderDB:
    """Crée une nouvelle commande, met à jour le stock et enregistre les mouvements."""
    logger.debug(f"[CRUD_V2] Création de commande pour user_id: {user_id} avec {len(order_in.items)} items")

    # 1. Vérifier existence utilisateur et adresses
    user = await get_user_by_id(db, user_id)
    if not user:
         raise HTTPException(status_code=404, detail=f"Utilisateur ID {user_id} non trouvé.")
    # Utiliser get_address_by_id refactorisé
    delivery_address = await get_address_by_id(db, order_in.delivery_address_id, user_id=user_id)
    if not delivery_address:
         raise HTTPException(status_code=404, detail=f"Adresse de livraison ID {order_in.delivery_address_id} invalide.")
    billing_address = await get_address_by_id(db, order_in.billing_address_id, user_id=user_id)
    if not billing_address:
         raise HTTPException(status_code=404, detail=f"Adresse de facturation ID {order_in.billing_address_id} invalide.")

    items_data_to_process = []
    variant_ids = [item.product_variant_id for item in order_in.items]
    variants_map: Dict[int, models.ProductVariantDB] = {}
    calculated_total = Decimal(0)

    try:
        # 2. Récupérer variations et vérifier stock
        if variant_ids:
            stmt = select(models.ProductVariantDB).where(models.ProductVariantDB.id.in_(variant_ids))
            result = await db.execute(stmt)
            existing_variants = result.scalars().all()
            variants_map = {v.id: v for v in existing_variants}

        for item in order_in.items:
            variant = variants_map.get(item.product_variant_id)
            if not variant:
                raise HTTPException(status_code=404, detail=f"Variation produit ID {item.product_variant_id} non trouvée.")

            # Vérification du stock (avant la boucle de mise à jour pour info rapide, mais la vraie vérif atomique est dans update_stock)
            stock_info = await get_stock_for_variant(db, variant.id)
            current_stock = stock_info.quantity if stock_info else 0
            if current_stock < item.quantity:
                 logger.warning(f"[CRUD_V2][TX] Stock insuffisant (pré-vérif) pour variant_id {variant.id} (demandé: {item.quantity}, dispo: {current_stock})")
                 raise HTTPException(status_code=409, detail=f"Stock insuffisant pour le produit SKU {variant.sku}. Disponible: {current_stock}")

            price = variant.price
            items_data_to_process.append({
                "variant_id": variant.id,
                "quantity": item.quantity,
                "price_at_order": price
            })
            calculated_total += (price * item.quantity)
        
        # Vérifier total (optionnel, dépend de la confiance dans le front-end)
        if calculated_total != order_in.total_amount:
             logger.warning(f"[CRUD_V2][TX] Incohérence de montant total (calculé: {calculated_total}, fourni: {order_in.total_amount}) - Utilisation du montant calculé.")
             final_total_amount = calculated_total
        else:
             final_total_amount = order_in.total_amount
        
        logger.debug(f"[CRUD_V2][TX] Stock vérifié, total calculé: {final_total_amount}")

        # 3. Créer l'en-tête de commande
        order_header_data = order_in.model_dump(exclude={'items'})
        order_header_data['user_id'] = user_id
        order_header_data['total_amount'] = final_total_amount # Utiliser le total vérifié/calculé
        new_order_db = models.OrderDB(**order_header_data)
        db.add(new_order_db)
        await db.flush() # Obtenir l'ID de la commande pour les items

        # 4. Créer OrderItems, MAJ Stock, créer StockMovements
        created_order_items_db = []
        for item_data in items_data_to_process:
             # 4a. Créer Order Item
             order_item_db = models.OrderItemDB(
                 order_id=new_order_db.id,
                 product_variant_id=item_data["variant_id"],
                 quantity=item_data["quantity"],
                 price_at_order=item_data["price_at_order"]
             )
             db.add(order_item_db)
             await db.flush() # Obtenir l'ID de l'order item pour le stock movement
             created_order_items_db.append(order_item_db) # Garder l'objet DB

             # 4b. Mettre à jour le stock (utilise la fonction refactorisée qui lève une erreur si stock < 0)
             # Cette opération est critique et atomique grâce à la requête UPDATE.
             try:
                  await update_stock_for_variant(db, item_data["variant_id"], -item_data["quantity"])
             except HTTPException as stock_error:
                  # Si update_stock_for_variant lève HTTPException (409 pour stock insuffisant), remonter l'erreur.
                  # Le rollback sera géré par get_db_session.
                  logger.error(f"[CRUD_V2][TX] Échec mise à jour stock pour variant {item_data['variant_id']}: {stock_error.detail}")
                  raise stock_error # Remonte l'erreur (probablement 409)
             
             # 4c. Enregistrer le mouvement de stock
             movement_data = models.StockMovementCreate(
                 product_variant_id=item_data["variant_id"],
                 quantity_change=-item_data["quantity"],
                 movement_type='order_fulfillment',
                 order_item_id=order_item_db.id # Lier au OrderItem créé
             )
             await record_stock_movement(db, movement_data) # Utilise la fonction refactorisée

        # Associer les items créés à l'objet OrderDB principal (si non fait par back_populates/cascade)
        # Normalement, l'ajout des OrderItemDB avec l'order_id correct suffit.
        # Mais on peut rafraîchir pour être sûr.
        await db.refresh(new_order_db, attribute_names=['items', 'user', 'delivery_address', 'billing_address'])

        logger.info(f"[CRUD_V2] Commande ID {new_order_db.id} créée avec succès pour user_id {user_id}.")
        # Le commit est géré par get_db_session

        return new_order_db

    except HTTPException as http_exc:
         # Le rollback est géré par get_db_session si l'exception remonte jusque là
         logger.warning(f"[CRUD_V2] HTTP Exception pendant création commande: {http_exc.detail}")
         raise http_exc
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur pendant la création de la commande pour user {user_id}: {e}", exc_info=True)
        # Le rollback est géré par get_db_session
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
    logger.debug(f"[CRUD_V2] Mise à jour statut commande ID: {order_id} -> {status}")
    allowed_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    if status not in allowed_statuses:
        logger.error(f"[CRUD_V2] Statut invalide '{status}' pour mise à jour commande.")
        raise HTTPException(status_code=400, detail=f"Statut invalide. Doit être l'un de: {', '.join(allowed_statuses)}")

    try:
        stmt = (
            sqlalchemy_update(models.OrderDB)
            .where(models.OrderDB.id == order_id)
            .values(status=status, updated_at=datetime.now(timezone.utc))
            .returning(models.OrderDB.id)
        )
        result = await db.execute(stmt)
        updated_id = result.scalar_one_or_none()

        if updated_id is None:
            logger.warning(f"[CRUD_V2] Commande ID {order_id} non trouvée pour mise à jour statut.")
            raise HTTPException(status_code=404, detail=f"Commande ID {order_id} non trouvée.")

        logger.info(f"[CRUD_V2] Statut de la commande ID {order_id} mis à jour à '{status}'.")

        # Recharger la commande pour retourner l'état complet
        updated_order = await get_order_by_id(db, order_id)
        if not updated_order:
             raise HTTPException(status_code=500, detail="Erreur interne: Impossible de récupérer la commande après mise à jour.")
        return updated_order

    except HTTPException as http_exc:
         raise http_exc
    except Exception as e:
        logger.error(f"[CRUD_V2] Erreur lors de la mise à jour du statut de la commande {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la mise à jour du statut de la commande.")
