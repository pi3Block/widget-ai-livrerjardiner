import logging
import psycopg2
from psycopg2 import OperationalError, ProgrammingError
from psycopg2.extras import Json # Pour insérer/récupérer JSONB
from psycopg2.pool import SimpleConnectionPool
from fastapi import HTTPException
import random
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from passlib.context import CryptContext # Ajout pour le hachage de mot de passe
# --- Supprimer imports PDF --- 
# import os
# from datetime import datetime
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib.units import inch
# from reportlab.lib.pagesizes import letter
# from reportlab.lib import colors

# --- Importer la configuration DB --- 
import config
# --- Importer la fonction PDF depuis pdf_utils --- 
# (Sera utilisé plus tard pour les devis/factures)
# from pdf_utils import generate_quote_pdf
# --- Importer les modèles Pydantic V3 ---
import models

logger = logging.getLogger(__name__)

# --- Initialisation du Pool de Connexions DB --- 
DB_POOL = None
try:
    if not config.POSTGRES_PASSWORD:
        logger.critical("Mot de passe DB non défini, impossible d'initialiser le pool.")
        # Lever une erreur ou utiliser un indicateur pour empêcher les opérations DB
    else:
        DB_POOL = SimpleConnectionPool(
            minconn=1,  # Garder au moins 1 connexion ouverte
            maxconn=10, # Maximum 10 connexions simultanées (ajuster selon besoin)
            dbname=config.POSTGRES_DB,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD,
            host=config.POSTGRES_HOST if hasattr(config, 'POSTGRES_HOST') else 'localhost', # Utiliser localhost si non défini
            port=config.POSTGRES_PORT if hasattr(config, 'POSTGRES_PORT') else '5432'      # Utiliser 5432 si non défini
        )
        logger.info("Pool de connexions DB initialisé.")
except OperationalError as pool_init_error:
    logger.critical(f"Erreur critique lors de l'initialisation du pool DB: {pool_init_error}")
    DB_POOL = None # Assurer que le pool est None si l'init échoue

# ----- Fonctions d'aide internes -----

def _get_db_conn():
    """Obtient une connexion du pool."""
    if not DB_POOL:
        logger.error("[CRUD] Pool DB non initialisé.")
        raise HTTPException(status_code=503, detail=config.DB_CONNECT_ERROR_MSG)
    try:
        return DB_POOL.getconn()
    except OperationalError as e:
        logger.error(f"[CRUD] Impossible d'obtenir une connexion DB du pool: {e}")
        raise HTTPException(status_code=503, detail=config.DB_CONNECT_ERROR_MSG)

def _release_db_conn(conn):
    """Remet une connexion dans le pool."""
    if DB_POOL and conn:
        DB_POOL.putconn(conn)
        logger.debug("[CRUD] Connexion DB retournée au pool.")

def _handle_db_error(e, conn=None, rollback=True):
    """Log l'erreur et lève une HTTPException appropriée."""
    if conn and rollback:
        conn.rollback()
        logger.debug("[CRUD] Rollback effectué.")
    
    if isinstance(e, OperationalError):
        logger.error(f"[CRUD] Erreur opérationnelle DB: {e}")
        raise HTTPException(status_code=503, detail=config.DB_CONNECT_ERROR_MSG)
    elif isinstance(e, ProgrammingError):
        logger.error(f"[CRUD] Erreur SQL (potentiellement schéma ou données): {e}")
        raise HTTPException(status_code=500, detail=config.DB_SQL_ERROR_MSG)
    elif isinstance(e, HTTPException):
        # Si c'est déjà une HTTPException (ex: Not Found), la remonter
        raise e
    else:
        logger.error(f"[CRUD] Erreur inattendue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne du serveur.")

# ----- Fonctions CRUD V3 -----

# --- CRUD: Products & Variants ---

def create_product(product: models.ProductCreate) -> models.Product:
    """Crée un nouveau produit de base."""
    logger.debug(f"[CRUD] Création du produit : {product.name}")
    conn = None
    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO products (name, base_description, category_id) VALUES (%s, %s, %s) RETURNING id, name, base_description, category_id, created_at, updated_at",
                (product.name, product.base_description, product.category_id)
            )
            result = cur.fetchone()
            conn.commit()
            logger.info(f"[CRUD] Produit créé avec ID: {result[0]}")
            # Mapper le résultat vers le modèle Pydantic Product (sans variants pour l'instant)
            return models.Product(
                id=result[0],
                name=result[1],
                base_description=result[2],
                category_id=result[3],
                created_at=result[4],
                updated_at=result[5]
            )
    except Exception as e:
        _handle_db_error(e, conn)
    finally:
        _release_db_conn(conn)

def create_product_variant(variant: models.ProductVariantCreate) -> models.ProductVariant:
    """Crée une nouvelle variation de produit et initialise son stock."""
    logger.debug(f"[CRUD] Création de la variation SKU: {variant.sku} pour produit ID: {variant.product_id}")
    conn = None
    try:
        conn = _get_db_conn()
        conn.autocommit = False # Transaction
        with conn.cursor() as cur:
            # 1. Insérer la variation
            cur.execute(
                "INSERT INTO product_variants (product_id, sku, attributes, price, image_url) VALUES (%s, %s, %s, %s, %s) RETURNING id, product_id, sku, attributes, price, image_url, created_at, updated_at",
                (variant.product_id, variant.sku, Json(variant.attributes) if variant.attributes else None, variant.price, variant.image_url)
            )
            result_variant = cur.fetchone()
            variant_id = result_variant[0]
            logger.debug(f"[CRUD] Variation insérée avec ID: {variant_id}")

            # 2. Initialiser le stock pour cette variation
            cur.execute(
                "INSERT INTO stock (product_variant_id, quantity, stock_alert_threshold) VALUES (%s, %s, %s) ON CONFLICT (product_variant_id) DO NOTHING", # Ignore si le stock existe déjà
                (variant_id, variant.initial_stock, variant.stock_alert_threshold)
            )
            logger.debug(f"[CRUD] Stock initialisé pour variation ID: {variant_id} (Quantité: {variant.initial_stock})")

            # 3. Enregistrer le mouvement de stock initial (optionnel mais bonne pratique)
            if variant.initial_stock > 0:
                cur.execute(
                    "INSERT INTO stock_movements (product_variant_id, quantity_change, movement_type) VALUES (%s, %s, %s)",
                    (variant_id, variant.initial_stock, 'initial_stock')
                )
                logger.debug(f"[CRUD] Mouvement de stock initial enregistré pour variation ID: {variant_id}")

            conn.commit()
            logger.info(f"[CRUD] Variation SKU {variant.sku} (ID: {variant_id}) créée avec succès.")
            # Mapper le résultat vers le modèle Pydantic ProductVariant (sans tags pour l'instant)
            return models.ProductVariant(
                id=result_variant[0],
                product_id=result_variant[1],
                sku=result_variant[2],
                attributes=result_variant[3],
                price=result_variant[4],
                image_url=result_variant[5],
                created_at=result_variant[6],
                updated_at=result_variant[7]
            )

    except Exception as e:
        _handle_db_error(e, conn, rollback=True)
    finally:
        if conn:
            conn.autocommit = True # Rétablir l'autocommit
            _release_db_conn(conn)

def get_product_variant_by_sku(sku: str) -> Optional[models.ProductVariant]:
    """Récupère une variation de produit par son SKU, incluant ses tags."""
    logger.debug(f"[CRUD] Recherche de la variation SKU: {sku} avec tags")
    conn = None
    try:
        conn = _get_db_conn()
        variant_data = None
        tags = []
        with conn.cursor() as cur:
            # 1. Récupérer la variation
            cur.execute(
                "SELECT id, product_id, sku, attributes, price, image_url, created_at, updated_at FROM product_variants WHERE sku = %s",
                (sku,)
            )
            result = cur.fetchone()
            if not result:
                logger.warning(f"[CRUD] Variation SKU {sku} non trouvée.")
                return None
            
            variant_id = result[0]
            variant_data = {
                "id": result[0],
                "product_id": result[1],
                "sku": result[2],
                "attributes": result[3],
                "price": result[4],
                "image_url": result[5],
                "created_at": result[6],
                "updated_at": result[7]
            }
            
            # 2. Récupérer les tags associés (dans la même transaction, pas besoin de get_tags_for_variant externe)
            cur.execute(
                 "SELECT t.id, t.name FROM tags t JOIN product_variant_tags pvt ON t.id = pvt.tag_id WHERE pvt.product_variant_id = %s",
                (variant_id,)
            )
            tag_results = cur.fetchall()
            for tag_result in tag_results:
                tags.append(models.Tag(id=tag_result[0], name=tag_result[1]))

        logger.debug(f"[CRUD] Variation SKU {sku} trouvée avec {len(tags)} tags.")
        # Mapper le résultat vers le modèle Pydantic
        variant_data["tags"] = tags
        return models.ProductVariant(**variant_data)
            
    except Exception as e:
        _handle_db_error(e, conn, rollback=False) # Pas de rollback pour un SELECT
    finally:
        _release_db_conn(conn)

# --- CRUD: Stock & Movements ---

def get_stock_for_variant(variant_id: int) -> int:
    """Récupère la quantité en stock pour une variation donnée."""
    logger.debug(f"[CRUD] Vérification du stock pour variant_id: {variant_id}")
    conn = None
    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT quantity FROM stock WHERE product_variant_id = %s", (variant_id,))
            result = cur.fetchone()
            stock_quantity = result[0] if result else 0
            logger.debug(f"[CRUD] Stock trouvé pour variant_id {variant_id}: {stock_quantity}")
            return stock_quantity
    except Exception as e:
        _handle_db_error(e, conn, rollback=False)
    finally:
        _release_db_conn(conn)

def update_stock_for_variant(conn, variant_id: int, quantity_change: int) -> int:
    """Met à jour le stock pour une variation (utilise une connexion existante pour transaction). Retourne la nouvelle quantité."""
    logger.debug(f"[CRUD][TX] Mise à jour stock pour variant_id: {variant_id}, changement: {quantity_change}")
    try:
        with conn.cursor() as cur:
            # Utiliser FOR UPDATE pour verrouiller la ligne pendant la transaction
            cur.execute(
                "UPDATE stock SET quantity = quantity + %s, last_updated = NOW() WHERE product_variant_id = %s RETURNING quantity",
                (quantity_change, variant_id)
            )
            result = cur.fetchone()
            if not result:
                # Le produit n'est pas dans la table stock, ce qui est une erreur si on essaie de le décrémenter
                logger.error(f"[CRUD][TX] Tentative de mise à jour du stock pour variant_id {variant_id} non trouvé dans la table stock.")
                raise HTTPException(status_code=404, detail=f"Stock non trouvé pour la variation ID {variant_id}.")
            
            new_quantity = result[0]
            # Vérifier si le stock est devenu négatif (si la logique métier l'interdit)
            if new_quantity < 0:
                logger.error(f"[CRUD][TX] Le stock pour variant_id {variant_id} deviendrait négatif ({new_quantity}). Rollback implicite.")
                raise HTTPException(status_code=409, detail="Stock insuffisant.") # 409 Conflict
            
            logger.debug(f"[CRUD][TX] Stock mis à jour pour variant_id {variant_id}. Nouvelle quantité: {new_quantity}")
            return new_quantity
    except Exception as e:
        # Ne pas gérer l'erreur ici, laisser la fonction appelante (ex: save_order) gérer le rollback global
        logger.error(f"[CRUD][TX] Erreur lors de la mise à jour du stock pour variant_id {variant_id}: {e}")
        raise # Remonter l'erreur pour rollback

def record_stock_movement(conn, variant_id: int, quantity_change: int, movement_type: str, order_item_id: Optional[int] = None):
    """Enregistre un mouvement de stock (utilise une connexion existante pour transaction)."""
    logger.debug(f"[CRUD][TX] Enregistrement mouvement stock pour variant_id {variant_id}, qte: {quantity_change}, type: {movement_type}")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO stock_movements (product_variant_id, quantity_change, movement_type, order_item_id) VALUES (%s, %s, %s, %s)",
                (variant_id, quantity_change, movement_type, order_item_id)
            )
        logger.debug("[CRUD][TX] Mouvement de stock enregistré.")
    except Exception as e:
        logger.error(f"[CRUD][TX] Erreur lors de l'enregistrement du mouvement de stock: {e}")
        raise # Remonter l'erreur pour rollback

# --- CRUD: Categories & Tags ---

def create_category(category: models.CategoryCreate) -> models.Category:
    """Crée une nouvelle catégorie."""
    logger.debug(f"[CRUD] Création catégorie: {category.name}")
    conn = None
    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO categories (name, description, parent_category_id) VALUES (%s, %s, %s) RETURNING id, name, description, parent_category_id, created_at, updated_at",
                (category.name, category.description, category.parent_category_id)
            )
            result = cur.fetchone()
            conn.commit()
            logger.info(f"[CRUD] Catégorie créée avec ID: {result[0]}")
            return models.Category(
                id=result[0],
                name=result[1],
                description=result[2],
                parent_category_id=result[3],
                created_at=result[4],
                updated_at=result[5]
            )
    except psycopg2.IntegrityError as e:
        # Gérer le cas où le nom de catégorie est déjà pris (contrainte UNIQUE)
        _handle_db_error(e, conn, rollback=True)
        logger.warning(f"[CRUD] Tentative de création de catégorie échouée (nom déjà existant?): {category.name}")
        raise HTTPException(status_code=409, detail=f"Le nom de catégorie '{category.name}' existe déjà.")
    except Exception as e:
        _handle_db_error(e, conn)
    finally:
        _release_db_conn(conn)

def get_category(category_id: int) -> Optional[models.Category]:
    """Récupère une catégorie par son ID."""
    logger.debug(f"[CRUD] Récupération catégorie ID: {category_id}")
    conn = None
    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, description, parent_category_id, created_at, updated_at FROM categories WHERE id = %s",
                (category_id,)
            )
            result = cur.fetchone()
            if not result:
                logger.warning(f"[CRUD] Catégorie ID {category_id} non trouvée.")
                return None
            return models.Category(
                id=result[0],
                name=result[1],
                description=result[2],
                parent_category_id=result[3],
                created_at=result[4],
                updated_at=result[5]
            )
    except Exception as e:
        _handle_db_error(e, conn, rollback=False)
    finally:
        _release_db_conn(conn)

def get_all_categories() -> List[models.Category]:
    """Récupère toutes les catégories."""
    logger.debug(f"[CRUD] Récupération de toutes les catégories")
    conn = None
    categories = []
    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, description, parent_category_id, created_at, updated_at FROM categories ORDER BY name")
            results = cur.fetchall()
            for result in results:
                categories.append(models.Category(
                    id=result[0],
                    name=result[1],
                    description=result[2],
                    parent_category_id=result[3],
                    created_at=result[4],
                    updated_at=result[5]
                ))
            logger.debug(f"[CRUD] {len(categories)} catégories récupérées.")
            return categories
    except Exception as e:
        _handle_db_error(e, conn, rollback=False)
    finally:
        _release_db_conn(conn)

def get_tag_by_name(conn, name: str) -> Optional[models.Tag]:
    """Récupère un tag par son nom (utilise connexion existante)."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM tags WHERE name = %s", (name,))
            result = cur.fetchone()
            if result:
                return models.Tag(id=result[0], name=result[1])
            return None
    except Exception as e:
         logger.error(f"[CRUD][TX] Erreur recherche tag '{name}': {e}")
         raise # Remonter pour rollback éventuel

def create_tag(conn, tag: models.TagCreate) -> models.Tag:
    """Crée un nouveau tag (utilise connexion existante)."""
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO tags (name) VALUES (%s) RETURNING id, name", (tag.name,))
            result = cur.fetchone()
            logger.debug(f"[CRUD][TX] Tag '{tag.name}' créé avec ID {result[0]}")
            return models.Tag(id=result[0], name=result[1])
    except psycopg2.IntegrityError:
         # Le tag existe déjà (contrainte unique), ce n'est pas une erreur fatale ici
         logger.warning(f"[CRUD][TX] Tentative de création du tag '{tag.name}' qui existe déjà.")
         # Essayer de le récupérer
         existing_tag = get_tag_by_name(conn, tag.name)
         if existing_tag:
             return existing_tag
         else:
             # Situation étrange, l'insert a échoué mais on ne le trouve pas ?!
             logger.error(f"[CRUD][TX] Erreur Integrity lors création tag '{tag.name}', mais impossible de le récupérer.")
             raise HTTPException(status_code=500, detail=f"Erreur lors de la création/récupération du tag '{tag.name}'.")
    except Exception as e:
         logger.error(f"[CRUD][TX] Erreur création tag '{tag.name}': {e}")
         raise # Remonter pour rollback éventuel

def get_or_create_tags(tag_names: List[str]) -> List[models.Tag]:
    """Récupère des tags existants ou les crée s'ils n'existent pas."""
    logger.debug(f"[CRUD] Récupération/Création des tags: {tag_names}")
    if not tag_names:
        return []
    
    conn = None
    created_tags = []
    try:
        conn = _get_db_conn()
        conn.autocommit = False # Transaction pour créer plusieurs tags
        
        for name in list(set(tag_names)): # Utiliser set pour dédoublonner
            if not name: continue # Ignorer les noms vides
            tag = get_tag_by_name(conn, name)
            if not tag:
                tag = create_tag(conn, models.TagCreate(name=name))
            created_tags.append(tag)
            
        conn.commit()
        logger.info(f"[CRUD] {len(created_tags)} tags récupérés/créés.")
        return created_tags
        
    except Exception as e:
        _handle_db_error(e, conn, rollback=True)
    finally:
        if conn:
             conn.autocommit = True
             _release_db_conn(conn)

def add_tags_to_variant(variant_id: int, tag_ids: List[int]):
    """Associe des tags (par ID) à une variation de produit."""
    if not tag_ids:
        return
    logger.debug(f"[CRUD] Association des tags {tag_ids} à la variation ID {variant_id}")
    conn = None
    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            # Utiliser ON CONFLICT DO NOTHING pour ignorer les associations déjà existantes
            sql = "INSERT INTO product_variant_tags (product_variant_id, tag_id) VALUES "
            values_template = [f"({variant_id}, %s)" for _ in tag_ids]
            sql += ", ".join(values_template)
            sql += " ON CONFLICT (product_variant_id, tag_id) DO NOTHING"
            
            cur.execute(sql, tag_ids)
            conn.commit()
            logger.info(f"[CRUD] Tags {tag_ids} associés à la variation {variant_id}.")
            
    except Exception as e:
        _handle_db_error(e, conn)
    finally:
        _release_db_conn(conn)

def get_tags_for_variant(conn, variant_id: int) -> List[models.Tag]:
    """Récupère les tags associés à une variation (utilise connexion existante)."""
    tags = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT t.id, t.name FROM tags t JOIN product_variant_tags pvt ON t.id = pvt.tag_id WHERE pvt.product_variant_id = %s",
                (variant_id,)
            )
            results = cur.fetchall()
            for result in results:
                tags.append(models.Tag(id=result[0], name=result[1]))
        return tags
    except Exception as e:
         logger.error(f"[CRUD][TX] Erreur récupération tags pour variant_id {variant_id}: {e}")
         raise # Remonter pour rollback éventuel

# --- CRUD: Recherche Produit ---

def list_products_with_variants(
    limit: int = 100, 
    offset: int = 0, 
    category_id: Optional[int] = None, 
    tag_names: Optional[List[str]] = None, # Liste de noms de tags
    search_term: Optional[str] = None
) -> List[models.Product]:
    """Récupère une liste de produits avec leurs variations, avec filtres et pagination."""
    logger.debug(f"[CRUD] Listage produits: limit={limit}, offset={offset}, cat={category_id}, tags={tag_names}, search={search_term}")
    conn = None
    try:
        conn = _get_db_conn()
        
        # Construire la requête dynamiquement
        base_query = """
            SELECT DISTINCT
                p.id as product_id, p.name as product_name, p.base_description, p.created_at as product_created_at, p.updated_at as product_updated_at,
                c.id as category_id, c.name as category_name, c.description as category_description, c.parent_category_id, 
                c.created_at as category_created_at, c.updated_at as category_updated_at,
                pv.id as variant_id, pv.sku, pv.attributes, pv.price, pv.image_url, 
                pv.created_at as variant_created_at, pv.updated_at as variant_updated_at
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN product_variants pv ON p.id = pv.product_id
        """
        joins = []
        conditions = []
        params = []

        # Filtre par catégorie
        if category_id is not None:
            conditions.append("p.category_id = %s")
            params.append(category_id)

        # Filtre par tags
        if tag_names:
            # Assurer que la variation a TOUS les tags spécifiés
            joins.append("LEFT JOIN product_variant_tags pvt ON pv.id = pvt.product_variant_id")
            joins.append("LEFT JOIN tags t ON pvt.tag_id = t.id")
            # Utiliser un tuple pour la clause IN
            conditions.append("t.name = ANY(%s)") # = ANY est plus simple que IN pour psycopg2 avec listes
            params.append(tag_names)
            # Pour forcer à avoir tous les tags, on pourrait ajouter un GROUP BY pv.id HAVING COUNT(DISTINCT t.name) = len(tag_names)
            # Mais cela complexifie beaucoup. Pour l'instant, on filtre si AU MOINS un tag correspond.
            # Alternative: Filtrer les product_id qui ont des variations correspondant à tous les tags dans une sous-requête.

        # Filtre par terme de recherche
        if search_term:
            search_pattern = f"%{search_term}%"
            # Utiliser des triple guillemets pour la chaîne multi-lignes
            conditions.append("""(
                p.name ILIKE %s OR 
                pv.sku ILIKE %s OR 
                p.base_description ILIKE %s
            )""")
            params.extend([search_pattern, search_pattern, search_pattern])

        # Assembler la requête
        query = base_query
        if joins:
            query += " " + " ".join(joins)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        # On récupère d'abord les product_id correspondant aux filtres avec pagination
        # Puis on récupère toutes les variations et détails pour ces produits
        paginated_product_ids_query = f"SELECT DISTINCT p.id FROM products p "
        if joins: paginated_product_ids_query += " " + " ".join(joins)
        if conditions: paginated_product_ids_query += " WHERE " + " AND ".join(conditions)
        paginated_product_ids_query += " ORDER BY p.id LIMIT %s OFFSET %s"
        
        final_params_ids = params + [limit, offset]
        
        product_ids_to_fetch = []
        with conn.cursor() as cur:
             cur.execute(paginated_product_ids_query, tuple(final_params_ids))
             results_ids = cur.fetchall()
             product_ids_to_fetch = [row[0] for row in results_ids]

        if not product_ids_to_fetch:
             return [] # Aucun produit ne correspond aux filtres

        # Maintenant, récupérer tous les détails pour les product_id trouvés
        details_query = """
            SELECT 
                p.id as product_id, p.name as product_name, p.base_description, p.created_at as product_created_at, p.updated_at as product_updated_at,
                c.id as category_id, c.name as category_name, c.description as category_description, c.parent_category_id, 
                c.created_at as category_created_at, c.updated_at as category_updated_at,
                pv.id as variant_id, pv.sku, pv.attributes, pv.price, pv.image_url, 
                pv.created_at as variant_created_at, pv.updated_at as variant_updated_at,
                t.id as tag_id, t.name as tag_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN product_variants pv ON p.id = pv.product_id
            LEFT JOIN product_variant_tags pvt ON pv.id = pvt.product_variant_id
            LEFT JOIN tags t ON pvt.tag_id = t.id
            WHERE p.id = ANY(%s) -- Récupérer seulement les produits paginés
            ORDER BY p.id, pv.id, t.id -- Ordonner pour faciliter le regroupement
        """
        
        products_dict: Dict[int, models.Product] = {}
        variants_dict: Dict[int, models.ProductVariant] = {}
        
        with conn.cursor() as cur:
            cur.execute(details_query, (product_ids_to_fetch,))
            results = cur.fetchall()

            for row in results:
                (product_id, product_name, base_description, product_created_at, product_updated_at,
                 category_id, category_name, category_description, parent_category_id, 
                 category_created_at, category_updated_at,
                 variant_id, sku, attributes, price, image_url, 
                 variant_created_at, variant_updated_at,
                 tag_id, tag_name) = row
                 
                # Créer/Récupérer le produit
                if product_id not in products_dict:
                    category = None
                    if category_id:
                        category = models.Category(
                            id=category_id, name=category_name, description=category_description,
                            parent_category_id=parent_category_id, created_at=category_created_at, 
                            updated_at=category_updated_at
                        )
                    products_dict[product_id] = models.Product(
                        id=product_id, name=product_name, base_description=base_description,
                        created_at=product_created_at, updated_at=product_updated_at,
                        category_id=category_id,
                        category=category,
                        variants=[]
                    )
                
                # Créer/Récupérer la variation (si elle existe)
                if variant_id:
                    if variant_id not in variants_dict:
                         variants_dict[variant_id] = models.ProductVariant(
                              id=variant_id, product_id=product_id, sku=sku, attributes=attributes,
                              price=price, image_url=image_url, created_at=variant_created_at,
                              updated_at=variant_updated_at, tags=[]
                         )
                         # Ajouter la variation à son produit parent
                         products_dict[product_id].variants.append(variants_dict[variant_id])
                    
                    # Ajouter le tag à la variation (si tag existe et pas déjà ajouté)
                    if tag_id:
                        tag = models.Tag(id=tag_id, name=tag_name)
                        # Éviter les doublons de tags pour une même variation
                        if not any(t.id == tag_id for t in variants_dict[variant_id].tags):
                             variants_dict[variant_id].tags.append(tag)
            
        # Retourner la liste des produits correspondant aux IDs paginés
        # Respecter l'ordre des IDs récupérés initialement peut être important
        ordered_products = [products_dict[pid] for pid in product_ids_to_fetch if pid in products_dict]
        logger.debug(f"[CRUD] {len(ordered_products)} produits récupérés avec détails pour listage.")
        return ordered_products

    except Exception as e:
        _handle_db_error(e, conn, rollback=False)
    finally:
        _release_db_conn(conn)

# --- CRUD: Users & Authentication ---

# Configuration Passlib
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe en clair contre un hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Génère le hash d'un mot de passe."""
    return pwd_context.hash(password)

def get_user_by_email(conn, email: str) -> Optional[models.User]:
    """Récupère un utilisateur par son email (utilise connexion existante)."""
    # Note : Ne retourne pas le hash du mot de passe
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, name, created_at, updated_at FROM users WHERE email = %s",
                (email,)
            )
            result = cur.fetchone()
            if not result:
                return None
            # TODO: Récupérer les adresses associées si nécessaire pour le modèle User complet
            return models.User(
                id=result[0],
                email=result[1],
                name=result[2],
                created_at=result[3],
                updated_at=result[4]
                # addresses=... 
            )
    except Exception as e:
         logger.error(f"[CRUD][TX] Erreur recherche user email '{email}': {e}")
         raise

def get_user_by_id(user_id: int) -> Optional[models.User]:
    """Récupère un utilisateur par son ID."""
    logger.debug(f"[CRUD] Récupération utilisateur ID: {user_id}")
    conn = None
    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, name, created_at, updated_at FROM users WHERE id = %s",
                (user_id,)
            )
            result = cur.fetchone()
            if not result:
                logger.warning(f"[CRUD] User ID {user_id} non trouvé.")
                return None
            
            # TODO: Récupérer les adresses associées
            addresses = get_user_addresses(user_id, conn) # Utiliser la même connexion

            return models.User(
                id=result[0],
                email=result[1],
                name=result[2],
                created_at=result[3],
                updated_at=result[4],
                addresses=addresses
            )
    except Exception as e:
        _handle_db_error(e, conn, rollback=False)
    finally:
        _release_db_conn(conn)

def create_user(user: models.UserCreate) -> models.User:
    """Crée un nouvel utilisateur."""
    logger.debug(f"[CRUD] Création utilisateur: {user.email}")
    hashed_password = get_password_hash(user.password)
    conn = None
    try:
        conn = _get_db_conn()
        # Vérifier si l'email existe déjà
        existing_user = get_user_by_email(conn, user.email)
        if existing_user:
             logger.warning(f"[CRUD] Tentative de création d'un utilisateur avec email existant: {user.email}")
             raise HTTPException(status_code=409, detail="Un compte avec cet email existe déjà.")

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s) RETURNING id, email, name, created_at, updated_at",
                (user.email, hashed_password, user.name)
            )
            result = cur.fetchone()
            conn.commit()
            logger.info(f"[CRUD] Utilisateur créé avec ID: {result[0]} pour email: {result[1]}")
            return models.User(
                id=result[0],
                email=result[1],
                name=result[2],
                created_at=result[3],
                updated_at=result[4]
                # addresses = [] # Pas d'adresse à la création initiale
            )
    except HTTPException as http_exc: # Remonter l'erreur 409
        raise http_exc
    except Exception as e:
        _handle_db_error(e, conn)
    finally:
        _release_db_conn(conn)

def authenticate_user(email: str, password: str) -> Optional[models.User]:
    """Authentifie un utilisateur par email et mot de passe."""
    logger.debug(f"[CRUD] Tentative d'authentification pour: {email}")
    conn = None
    try:
        conn = _get_db_conn()
        # Récupérer l'utilisateur ET son hash de mot de passe
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash, name, created_at, updated_at FROM users WHERE email = %s",
                (email,)
            )
            result = cur.fetchone()
            if not result:
                logger.warning(f"[AUTH] Utilisateur non trouvé: {email}")
                return None # Utilisateur non trouvé
            
            user_id, db_email, db_hashed_password, db_name, db_created_at, db_updated_at = result
            
            # Vérifier le mot de passe
            if not verify_password(password, db_hashed_password):
                logger.warning(f"[AUTH] Mot de passe incorrect pour: {email}")
                return None # Mot de passe incorrect

            logger.info(f"[AUTH] Authentification réussie pour: {email} (ID: {user_id})")
            # Retourner l'utilisateur SANS le hash
            # TODO: Récupérer les adresses
            return models.User(
                id=user_id,
                email=db_email,
                name=db_name,
                created_at=db_created_at,
                updated_at=db_updated_at
                # addresses=...
            )

    except Exception as e:
        _handle_db_error(e, conn, rollback=False)
    finally:
        _release_db_conn(conn)

# --- CRUD: Addresses ---

def create_user_address(user_id: int, address: models.AddressCreate) -> models.Address:
    """Ajoute une nouvelle adresse pour un utilisateur."""
    logger.debug(f"[CRUD] Ajout d'adresse pour user_id: {user_id}")
    conn = None
    try:
        conn = _get_db_conn()
        conn.autocommit = False # Transaction si on gère is_default

        # Si la nouvelle adresse doit être par défaut, désactiver les autres
        if address.is_default:
            set_default_address(user_id, None, conn=conn) # Désactive tous les défauts existants

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO addresses (user_id, street, city, zip_code, country, is_default) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, user_id, street, city, zip_code, country, is_default, created_at, updated_at",
                (user_id, address.street, address.city, address.zip_code, address.country, address.is_default)
            )
            result = cur.fetchone()
            conn.commit()
            logger.info(f"[CRUD] Adresse créée ID: {result[0]} pour user_id: {user_id}")
            return models.Address(
                 id=result[0],
                 user_id=result[1],
                 street=result[2],
                 city=result[3],
                 zip_code=result[4],
                 country=result[5],
                 is_default=result[6],
                 created_at=result[7],
                 updated_at=result[8]
            )
    except Exception as e:
        _handle_db_error(e, conn)
    finally:
        if conn:
            conn.autocommit = True
            _release_db_conn(conn)

def get_user_addresses(user_id: int, conn=None) -> List[models.Address]:
    """Récupère toutes les adresses d'un utilisateur."""
    logger.debug(f"[CRUD] Récupération des adresses pour user_id: {user_id}")
    release_conn = False
    if conn is None:
        conn = _get_db_conn()
        release_conn = True
        
    addresses = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, street, city, zip_code, country, is_default, created_at, updated_at FROM addresses WHERE user_id = %s ORDER BY is_default DESC, created_at DESC",
                (user_id,)
            )
            results = cur.fetchall()
            for result in results:
                addresses.append(models.Address(
                    id=result[0],
                    user_id=result[1],
                    street=result[2],
                    city=result[3],
                    zip_code=result[4],
                    country=result[5],
                    is_default=result[6],
                    created_at=result[7],
                    updated_at=result[8]
                ))
            logger.debug(f"[CRUD] {len(addresses)} adresses récupérées pour user_id {user_id}.")
            return addresses
    except Exception as e:
        # Ne pas rollback si on utilise une connexion externe
        _handle_db_error(e, conn, rollback=(release_conn))
    finally:
        if release_conn:
            _release_db_conn(conn)

def get_address_by_id(address_id: int, user_id: Optional[int] = None) -> Optional[models.Address]:
    """Récupère une adresse par son ID, en vérifiant éventuellement l'appartenance à un utilisateur."""
    logger.debug(f"[CRUD] Récupération adresse ID: {address_id} (pour user_id: {user_id})")
    conn = None
    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            sql = "SELECT id, user_id, street, city, zip_code, country, is_default, created_at, updated_at FROM addresses WHERE id = %s"
            params = [address_id]
            if user_id is not None:
                sql += " AND user_id = %s"
                params.append(user_id)
                
            cur.execute(sql, tuple(params))
            result = cur.fetchone()
            if not result:
                logger.warning(f"[CRUD] Adresse ID {address_id} non trouvée (ou n'appartient pas à user_id {user_id}).")
                return None
            return models.Address(
                 id=result[0],
                 user_id=result[1],
                 street=result[2],
                 city=result[3],
                 zip_code=result[4],
                 country=result[5],
                 is_default=result[6],
                 created_at=result[7],
                 updated_at=result[8]
            )
    except Exception as e:
        _handle_db_error(e, conn, rollback=False)
    finally:
        _release_db_conn(conn)

def set_default_address(user_id: int, address_id_to_set: Optional[int], conn=None):
    """Définit une adresse comme défaut pour un utilisateur, en désactivant les autres."""
    logger.debug(f"[CRUD] Définition de l'adresse par défaut pour user_id: {user_id} -> address_id: {address_id_to_set}")
    release_conn = False
    if conn is None:
        conn = _get_db_conn()
        release_conn = True
        conn.autocommit = False # Transaction nécessaire

    try:
        with conn.cursor() as cur:
            # 1. Désactiver toutes les adresses par défaut actuelles pour cet utilisateur
            cur.execute(
                "UPDATE addresses SET is_default = FALSE WHERE user_id = %s AND is_default = TRUE",
                (user_id,)
            )
            logger.debug(f"[CRUD][TX] Anciennes adresses par défaut désactivées pour user_id: {user_id}")
            
            # 2. Activer la nouvelle adresse par défaut (si une est spécifiée)
            if address_id_to_set is not None:
                cur.execute(
                    "UPDATE addresses SET is_default = TRUE WHERE id = %s AND user_id = %s",
                    (address_id_to_set, user_id)
                )
                # Vérifier si la mise à jour a fonctionné (l'adresse existe et appartient à l'utilisateur)
                if cur.rowcount == 0:
                    logger.error(f"[CRUD][TX] Impossible de définir l'adresse par défaut: ID {address_id_to_set} non trouvée ou n'appartient pas à l'utilisateur {user_id}.")
                    raise HTTPException(status_code=404, detail="Adresse non trouvée ou invalide pour cet utilisateur.")
                logger.debug(f"[CRUD][TX] Adresse ID {address_id_to_set} définie comme défaut pour user_id: {user_id}")

        if release_conn: # Commit seulement si on gère la transaction ici
            conn.commit()
            logger.info(f"[CRUD] Adresse par défaut mise à jour pour user_id: {user_id}")
            
    except Exception as e:
        # Ne pas rollback si on utilise une connexion externe
        _handle_db_error(e, conn, rollback=(release_conn))
    finally:
        if release_conn:
            conn.autocommit = True
            _release_db_conn(conn)

# --- Placeholders pour autres CRUD User/Address ---

def update_user(user_id: int, user_update: models.UserCreate) -> Optional[models.User]:
     # TODO: Implémenter (attention à la mise à jour du mot de passe)
     pass

def update_user_address(address_id: int, address_update: models.AddressCreate, user_id: int) -> Optional[models.Address]:
    # TODO: Implémenter (vérifier que l'adresse appartient à user_id)
    pass

def delete_user_address(address_id: int, user_id: int):
    # TODO: Implémenter (vérifier que l'adresse appartient à user_id)
    pass

# --- CRUD: Quotes & Quote Items ---

def create_quote(user_id: int, quote_in: models.QuoteCreate) -> models.Quote:
    """Crée un nouveau devis avec ses lignes."""
    logger.debug(f"[CRUD] Création d'un devis pour user_id: {user_id} avec {len(quote_in.items)} items")
    conn = None
    items_to_insert = []
    
    try:
        conn = _get_db_conn()
        conn.autocommit = False # Transaction

        # 1. Vérifier l'existence et récupérer les prix actuels des variations
        variant_cache = {} # Cache simple pour éviter requêtes répétées si même SKU dans le devis
        for item in quote_in.items:
            if item.product_variant_id in variant_cache:
                variant = variant_cache[item.product_variant_id]
            else:
                # TODO: Améliorer en récupérant toutes les variations en une seule requête si possible
                variant = get_product_variant_by_id(conn, item.product_variant_id) # get_product_variant_by_id est à créer
                if not variant:
                    logger.error(f"[CRUD][TX] Variation ID {item.product_variant_id} non trouvée pour le devis.")
                    raise HTTPException(status_code=404, detail=f"Variation produit ID {item.product_variant_id} non trouvée.")
                variant_cache[item.product_variant_id] = variant
                
            items_to_insert.append({
                "product_variant_id": variant.id,
                "quantity": item.quantity,
                "price_at_quote": variant.price # Utiliser le prix actuel de la variation
            })

        # 2. Créer l'en-tête du devis
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO quotes (user_id, status, expires_at) VALUES (%s, %s, %s) RETURNING id, quote_date, created_at, updated_at",
                (user_id, quote_in.status, quote_in.expires_at)
            )
            result_quote = cur.fetchone()
            quote_id = result_quote[0]
            logger.debug(f"[CRUD][TX] En-tête devis créé ID: {quote_id}")

            # 3. Insérer les lignes du devis
            if items_to_insert:
                sql_items = "INSERT INTO quote_items (quote_id, product_variant_id, quantity, price_at_quote) VALUES "
                values_template = [f"({quote_id}, %s, %s, %s)" for _ in items_to_insert]
                sql_items += ", ".join(values_template)
                
                params_items = []
                for item_data in items_to_insert:
                    params_items.extend([item_data["product_variant_id"], item_data["quantity"], item_data["price_at_quote"]])
                    
                cur.execute(sql_items, tuple(params_items))
                logger.debug(f"[CRUD][TX] {len(items_to_insert)} lignes insérées pour devis ID: {quote_id}")

            conn.commit()
            logger.info(f"[CRUD] Devis ID {quote_id} créé avec succès pour user_id {user_id}.")

            # 4. Re-récupérer le devis complet pour le retourner (plus simple que de construire l'objet manuellement)
            # Attention: get_quote_by_id doit être implémenté
            created_quote = get_quote_by_id(quote_id)
            if not created_quote: # Ne devrait pas arriver
                 logger.error(f"[CRUD] Impossible de récupérer le devis ID {quote_id} juste après création.")
                 raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération du devis créé.")
            return created_quote

    except Exception as e:
        _handle_db_error(e, conn, rollback=True)
    finally:
        if conn:
            conn.autocommit = True
            _release_db_conn(conn)

def get_product_variant_by_id(conn, variant_id: int) -> Optional[models.ProductVariant]:
    """Récupère une variation par son ID (utilise connexion existante)."""
    # Similaire à get_product_variant_by_sku mais par ID
    try:
        variant_data = None
        tags = []
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, product_id, sku, attributes, price, image_url, created_at, updated_at FROM product_variants WHERE id = %s",
                (variant_id,)
            )
            result = cur.fetchone()
            if not result:
                return None
            variant_data = {
                "id": result[0],
                "product_id": result[1],
                "sku": result[2],
                "attributes": result[3],
                "price": result[4],
                "image_url": result[5],
                "created_at": result[6],
                "updated_at": result[7]
            }
            tags = get_tags_for_variant(conn, variant_id) # Réutiliser la fonction existante
            variant_data["tags"] = tags
            return models.ProductVariant(**variant_data)
    except Exception as e:
        logger.error(f"[CRUD][TX] Erreur récupération variant ID {variant_id}: {e}")
        raise

def get_quote_by_id(quote_id: int) -> Optional[models.Quote]:
    """Récupère un devis complet par son ID."""
    logger.debug(f"[CRUD] Récupération devis ID: {quote_id}")
    conn = None
    try:
        conn = _get_db_conn()
        quote: Optional[models.Quote] = None
        quote_items: List[models.QuoteItem] = []

        with conn.cursor() as cur:
            # 1. Récupérer l'en-tête du devis
            cur.execute(
                "SELECT id, user_id, quote_date, status, expires_at, created_at, updated_at FROM quotes WHERE id = %s",
                (quote_id,)
            )
            result_quote = cur.fetchone()
            if not result_quote:
                logger.warning(f"[CRUD] Devis ID {quote_id} non trouvé.")
                return None

            # 2. Récupérer les lignes du devis
            cur.execute(
                "SELECT id, quote_id, product_variant_id, quantity, price_at_quote, created_at, updated_at FROM quote_items WHERE quote_id = %s ORDER BY id",
                (quote_id,)
            )
            results_items = cur.fetchall()

            # 3. Récupérer les détails des variations pour chaque ligne (peut être optimisé)
            variant_ids = [item[2] for item in results_items]
            variants_details = {}
            if variant_ids:
                # Utiliser get_product_variant_by_id pour chaque variation
                for var_id in variant_ids:
                     # Attention: Appels multiples à la DB ici. Possible optimisation.
                     variant = get_product_variant_by_id(conn, var_id)
                     if variant: # Gérer le cas où la variation aurait été supprimée
                          variants_details[var_id] = variant
            
            # 4. Assembler les objets QuoteItem
            for item_res in results_items:
                variant_detail = variants_details.get(item_res[2])
                quote_items.append(models.QuoteItem(
                    id=item_res[0],
                    quote_id=item_res[1],
                    product_variant_id=item_res[2],
                    quantity=item_res[3],
                    price_at_quote=item_res[4],
                    created_at=item_res[5],
                    updated_at=item_res[6],
                    variant=variant_detail # Inclure les détails de la variation
                ))
            
            # 5. Assembler l'objet Quote final (récupérer User si besoin)
            # user = get_user_by_id(result_quote[1]) # Optionnel
            quote = models.Quote(
                id=result_quote[0],
                user_id=result_quote[1],
                quote_date=result_quote[2],
                status=result_quote[3],
                expires_at=result_quote[4],
                created_at=result_quote[5],
                updated_at=result_quote[6],
                items=quote_items
                # user=user # Optionnel
            )
            
        logger.debug(f"[CRUD] Devis ID {quote_id} récupéré avec {len(quote_items)} lignes.")
        return quote

    except Exception as e:
        _handle_db_error(e, conn, rollback=False)
    finally:
        _release_db_conn(conn)

def list_user_quotes(user_id: int, limit: int = 20, offset: int = 0) -> List[models.Quote]:
    """Liste les devis pour un utilisateur donné (en-têtes seulement pour l'instant)."""
    # TODO: Ajouter la récupération des lignes si nécessaire (peut être coûteux)
    logger.debug(f"[CRUD] Listage des devis pour user_id: {user_id} (limit={limit}, offset={offset})")
    conn = None
    quotes_list = []
    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, quote_date, status, expires_at, created_at, updated_at FROM quotes WHERE user_id = %s ORDER BY quote_date DESC LIMIT %s OFFSET %s",
                (user_id, limit, offset)
            )
            results = cur.fetchall()
            for res in results:
                 # Pour l'instant, on ne charge pas les items ni l'utilisateur pour la liste
                 quotes_list.append(models.Quote(
                    id=res[0],
                    user_id=res[1],
                    quote_date=res[2],
                    status=res[3],
                    expires_at=res[4],
                    created_at=res[5],
                    updated_at=res[6],
                    items=[] # Laisser vide pour la liste
                 ))
        logger.debug(f"[CRUD] {len(quotes_list)} devis récupérés pour user_id {user_id}.")
        return quotes_list

    except Exception as e:
        _handle_db_error(e, conn, rollback=False)
    finally:
        _release_db_conn(conn)

def update_quote_status(quote_id: int, status: str) -> Optional[models.Quote]:
    """Met à jour le statut d'un devis."""
    logger.debug(f"[CRUD] Mise à jour statut devis ID: {quote_id} -> {status}")
    conn = None
    allowed_statuses = ['pending', 'accepted', 'rejected', 'expired'] # Exemple
    if status not in allowed_statuses:
        logger.error(f"[CRUD] Statut invalide '{status}' pour mise à jour devis.")
        raise HTTPException(status_code=400, detail=f"Statut invalide. Doit être l'un de: {', '.join(allowed_statuses)}")

    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE quotes SET status = %s WHERE id = %s RETURNING id",
                (status, quote_id)
            )
            result = cur.fetchone()
            if not result:
                logger.warning(f"[CRUD] Devis ID {quote_id} non trouvé pour mise à jour statut.")
                raise HTTPException(status_code=404, detail=f"Devis ID {quote_id} non trouvé.")
                
            conn.commit()
            logger.info(f"[CRUD] Statut du devis ID {quote_id} mis à jour à '{status}'.")
            # Retourner le devis mis à jour (en le rechargeant)
            return get_quote_by_id(quote_id)
            
    except Exception as e:
        _handle_db_error(e, conn)
    finally:
        _release_db_conn(conn)

# --- CRUD: Orders & Order Items ---

def create_order(user_id: int, order_in: models.OrderCreate) -> models.Order:
    """Crée une nouvelle commande multi-items, met à jour le stock et enregistre les mouvements."""
    logger.debug(f"[CRUD] Tentative de création de commande pour user_id: {user_id} avec {len(order_in.items)} items")
    conn = None
    items_to_process = [] # Contiendra {variant_id, quantity, price_at_order}
    calculated_total = Decimal(0)

    try:
        conn = _get_db_conn()
        conn.autocommit = False # Transaction START
        logger.debug("[CRUD][TX] Démarrage transaction pour création commande.")

        # 1. Vérifier existence utilisateur et adresses (pour s'assurer qu'ils existent avant la FK)
        user = get_user_by_id(user_id) # Utilise sa propre connexion, pourrait être optimisé
        if not user:
             raise HTTPException(status_code=404, detail=f"Utilisateur ID {user_id} non trouvé.")
        delivery_address = get_address_by_id(order_in.delivery_address_id, user_id=user_id) # Vérifie l'appartenance
        if not delivery_address:
             raise HTTPException(status_code=404, detail=f"Adresse de livraison ID {order_in.delivery_address_id} invalide pour cet utilisateur.")
        billing_address = get_address_by_id(order_in.billing_address_id, user_id=user_id) # Vérifie l'appartenance
        if not billing_address:
             raise HTTPException(status_code=404, detail=f"Adresse de facturation ID {order_in.billing_address_id} invalide pour cet utilisateur.")

        # 2. Vérifier stock et récupérer prix pour chaque item
        variant_cache = {} # Pour éviter requêtes répétées
        for item in order_in.items:
            if item.product_variant_id in variant_cache:
                variant = variant_cache[item.product_variant_id]
            else:
                 # Utiliser la connexion de la transaction en cours
                variant = get_product_variant_by_id(conn, item.product_variant_id)
                if not variant:
                    logger.error(f"[CRUD][TX] Variation ID {item.product_variant_id} non trouvée pour la commande.")
                    raise HTTPException(status_code=404, detail=f"Variation produit ID {item.product_variant_id} non trouvée.")
                variant_cache[item.product_variant_id] = variant
            
            # Vérification du stock DANS la transaction pour locking potentiel (via update_stock plus tard)
            current_stock = get_stock_for_variant(item.product_variant_id) # Peut utiliser une connexion séparée, ok pour juste lire
            if current_stock < item.quantity:
                 logger.warning(f"[CRUD][TX] Stock insuffisant pour variant_id {variant.id} (demandé: {item.quantity}, dispo: {current_stock})")
                 raise HTTPException(status_code=409, detail=f"Stock insuffisant pour le produit SKU {variant.sku}. Disponible: {current_stock}")

            price = variant.price
            items_to_process.append({
                "variant_id": variant.id,
                "quantity": item.quantity,
                "price_at_order": price
            })
            calculated_total += (price * item.quantity)
        
        # Vérifier si le total calculé correspond au total fourni (sécurité/cohérence)
        # Note: utiliser isclose pour comparer les Decimals si nécessaire
        if calculated_total != order_in.total_amount:
             logger.warning(f"[CRUD][TX] Incohérence de montant total (calculé: {calculated_total}, fourni: {order_in.total_amount})")
             # On pourrait lever une erreur ou juste utiliser le montant calculé
             # raise HTTPException(status_code=400, detail="Le montant total de la commande est incorrect.")
             final_total_amount = calculated_total # Utiliser le montant calculé, plus sûr
        else:
             final_total_amount = order_in.total_amount
        
        logger.debug(f"[CRUD][TX] Stock vérifié, total calculé: {final_total_amount}")

        # 3. Créer l'en-tête de commande
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (user_id, status, total_amount, delivery_address_id, billing_address_id) VALUES (%s, %s, %s, %s, %s) RETURNING id, order_date, created_at, updated_at",
                (user_id, order_in.status, final_total_amount, order_in.delivery_address_id, order_in.billing_address_id)
            )
            result_order = cur.fetchone()
            order_id = result_order[0]
            order_date = result_order[1]
            order_created_at = result_order[2]
            order_updated_at = result_order[3]
            logger.debug(f"[CRUD][TX] En-tête commande créé ID: {order_id}")

            # 4. Traiter chaque ligne: créer order_item, MAJ stock, créer stock_movement
            created_order_items = []
            for item_data in items_to_process:
                 # 4a. Créer Order Item
                 cur.execute(
                     "INSERT INTO order_items (order_id, product_variant_id, quantity, price_at_order) VALUES (%s, %s, %s, %s) RETURNING id, created_at, updated_at",
                     (order_id, item_data["variant_id"], item_data["quantity"], item_data["price_at_order"])
                 )
                 result_item = cur.fetchone()
                 order_item_id = result_item[0]
                 logger.debug(f"[CRUD][TX] Ligne commande créée ID: {order_item_id} pour variant_id {item_data['variant_id']}")
                 
                 # Stocker les détails pour l'objet final
                 created_order_items.append(models.OrderItem(
                     id=order_item_id,
                     order_id=order_id,
                     product_variant_id=item_data["variant_id"],
                     quantity=item_data["quantity"],
                     price_at_order=item_data["price_at_order"],
                     created_at=result_item[1],
                     updated_at=result_item[2],
                     # variant=variant_cache[item_data["variant_id"]] # On peut le charger ici
                 ))

                 # 4b. Mettre à jour le stock (décrémenter)
                 # La fonction update_stock_for_variant utilise déjà la connexion et gère l'erreur si stock < 0
                 update_stock_for_variant(conn, item_data["variant_id"], -item_data["quantity"]) 
                 
                 # 4c. Enregistrer le mouvement de stock
                 record_stock_movement(conn, item_data["variant_id"], -item_data["quantity"], 'order_fulfillment', order_item_id=order_item_id)

            # 5. Commit la transaction
            conn.commit()
            logger.info(f"[CRUD] Commande ID {order_id} créée avec succès pour user_id {user_id}.")

            # 6. Construire l'objet Order complet à retourner
            # Recharger les relations si nécessaire ou construire manuellement
            return models.Order(
                id=order_id,
                user_id=user_id,
                order_date=order_date,
                status=order_in.status,
                total_amount=final_total_amount,
                delivery_address_id=order_in.delivery_address_id,
                billing_address_id=order_in.billing_address_id,
                created_at=order_created_at,
                updated_at=order_updated_at,
                items=created_order_items,
                user=user, # Déjà récupéré
                delivery_address=delivery_address, # Déjà récupéré
                billing_address=billing_address # Déjà récupéré
            )

    except HTTPException as http_exc:
        if conn: conn.rollback() # Assurer le rollback si l'erreur vient de la logique interne
        logger.warning(f"[CRUD] HTTP Exception pendant création commande: {http_exc.detail}")
        raise http_exc # Remonter l'erreur HTTP
    except Exception as e:
        logger.error(f"[CRUD] Erreur pendant la création de la commande.")
        # _handle_db_error gère le rollback
        _handle_db_error(e, conn, rollback=True)
    finally:
        if conn:
            conn.autocommit = True # Rétablir l'autocommit
            _release_db_conn(conn)
            logger.debug("[CRUD][TX] Fin transaction création commande.")

def get_order_by_id(order_id: int) -> Optional[models.Order]:
    """Récupère une commande complète par son ID."""
    logger.debug(f"[CRUD] Récupération commande ID: {order_id}")
    conn = None
    try:
        conn = _get_db_conn()
        order: Optional[models.Order] = None
        order_items: List[models.OrderItem] = []

        with conn.cursor() as cur:
            # 1. Récupérer l'en-tête de commande
            cur.execute(
                "SELECT id, user_id, order_date, status, total_amount, delivery_address_id, billing_address_id, created_at, updated_at FROM orders WHERE id = %s",
                (order_id,)
            )
            result_order = cur.fetchone()
            if not result_order:
                logger.warning(f"[CRUD] Commande ID {order_id} non trouvée.")
                return None
                
            order_data = dict(zip(["id", "user_id", "order_date", "status", "total_amount", "delivery_address_id", "billing_address_id", "created_at", "updated_at"], result_order))

            # 2. Récupérer les lignes de la commande
            cur.execute(
                "SELECT id, order_id, product_variant_id, quantity, price_at_order, created_at, updated_at FROM order_items WHERE order_id = %s ORDER BY id",
                (order_id,)
            )
            results_items = cur.fetchall()
            
            # 3. Récupérer détails variations, utilisateur, adresses (peut être optimisé)
            variant_ids = list(set([item[2] for item in results_items]))
            variants_details = {}
            if variant_ids:
                 for var_id in variant_ids:
                     variant = get_product_variant_by_id(conn, var_id)
                     if variant:
                          variants_details[var_id] = variant
                          
            user_details = get_user_by_id(order_data["user_id"]) # Utilise une autre connexion, ok ici
            delivery_address_details = get_address_by_id(order_data["delivery_address_id"]) # Idem
            billing_address_details = get_address_by_id(order_data["billing_address_id"]) # Idem

            # 4. Assembler les objets OrderItem
            for item_res in results_items:
                variant_detail = variants_details.get(item_res[2])
                order_items.append(models.OrderItem(
                    id=item_res[0],
                    order_id=item_res[1],
                    product_variant_id=item_res[2],
                    quantity=item_res[3],
                    price_at_order=item_res[4],
                    created_at=item_res[5],
                    updated_at=item_res[6],
                    variant=variant_detail
                ))
                
            # 5. Assembler l'objet Order final
            order_data["items"] = order_items
            order_data["user"] = user_details
            order_data["delivery_address"] = delivery_address_details
            order_data["billing_address"] = billing_address_details
            order = models.Order(**order_data)
            
        logger.debug(f"[CRUD] Commande ID {order_id} récupérée avec {len(order_items)} lignes.")
        return order

    except Exception as e:
        _handle_db_error(e, conn, rollback=False)
    finally:
        _release_db_conn(conn)

def list_user_orders(user_id: int, limit: int = 20, offset: int = 0) -> List[models.Order]:
    """Liste les commandes pour un utilisateur donné (en-têtes seulement)."""
    logger.debug(f"[CRUD] Listage des commandes pour user_id: {user_id} (limit={limit}, offset={offset})")
    conn = None
    orders_list = []
    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, order_date, status, total_amount, delivery_address_id, billing_address_id, created_at, updated_at FROM orders WHERE user_id = %s ORDER BY order_date DESC LIMIT %s OFFSET %s",
                (user_id, limit, offset)
            )
            results = cur.fetchall()
            for res in results:
                 order_data = dict(zip(["id", "user_id", "order_date", "status", "total_amount", "delivery_address_id", "billing_address_id", "created_at", "updated_at"], res))
                 order_data["items"] = [] # Laisser vide pour la liste
                 orders_list.append(models.Order(**order_data))
                 
        logger.debug(f"[CRUD] {len(orders_list)} commandes récupérées pour user_id {user_id}.")
        return orders_list

    except Exception as e:
        _handle_db_error(e, conn, rollback=False)
    finally:
        _release_db_conn(conn)

def update_order_status(order_id: int, status: str) -> Optional[models.Order]:
    """Met à jour le statut d'une commande."""
    logger.debug(f"[CRUD] Mise à jour statut commande ID: {order_id} -> {status}")
    conn = None
    # TODO: Définir les statuts autorisés (peut-être dans config ou enum)
    allowed_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled'] 
    if status not in allowed_statuses:
        logger.error(f"[CRUD] Statut invalide '{status}' pour mise à jour commande.")
        raise HTTPException(status_code=400, detail=f"Statut invalide. Doit être l'un de: {', '.join(allowed_statuses)}")

    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE orders SET status = %s WHERE id = %s RETURNING id",
                (status, order_id)
            )
            result = cur.fetchone()
            if not result:
                logger.warning(f"[CRUD] Commande ID {order_id} non trouvée pour mise à jour statut.")
                raise HTTPException(status_code=404, detail=f"Commande ID {order_id} non trouvée.")
                
            conn.commit()
            logger.info(f"[CRUD] Statut de la commande ID {order_id} mis à jour à '{status}'.")
            # Retourner la commande mise à jour
            return get_order_by_id(order_id)
            
    except Exception as e:
        _handle_db_error(e, conn)
    finally:
        _release_db_conn(conn)
