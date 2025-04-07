import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

import sqlalchemy
from sqlalchemy import select, func, update as sqlalchemy_update, delete as sqlalchemy_delete, case
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, contains_eager, joinedload

# Modèles SQLAlchemy DB (depuis nouvel emplacement)
from src.database import models

# Domaine Products
from src.products.domain.entities import Category, Tag, Product, ProductVariant, Stock
from src.products.domain.repositories import (
    AbstractCategoryRepository, AbstractTagRepository, AbstractProductRepository, 
    AbstractProductVariantRepository, AbstractStockRepository
)
from src.products.domain.exceptions import (
    CategoryNotFoundException, InvalidOperationException, ProductNotFoundException, 
    VariantNotFoundException, DuplicateSKUException, StockNotFoundException, 
    InsufficientStockException
)

logger = logging.getLogger(__name__)

class SQLAlchemyCategoryRepository(AbstractCategoryRepository):
    """Implémentation SQLAlchemy du repository de Catégories."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, category_id: int) -> Optional[Category]:
        """Récupère une catégorie par son ID."""
        stmt = select(models.CategoryDB).where(models.CategoryDB.id == category_id)
        result = await self.session.execute(stmt)
        category_db = result.scalar_one_or_none()
        if category_db:
            return Category.model_validate(category_db)
        # Conforme à l'interface, retourne None si non trouvé.
        # Lever CategoryNotFoundException serait une alternative si le contrat changeait.
        logger.debug(f"Catégorie ID {category_id} non trouvée dans get().")
        return None

    async def get_by_name(self, name: str) -> Optional[Category]:
        """Récupère une catégorie par son nom (insensible à la casse)."""
        stmt = select(models.CategoryDB).where(func.lower(models.CategoryDB.name) == name.lower())
        result = await self.session.execute(stmt)
        category_db = result.scalar_one_or_none()
        if category_db:
            return Category.model_validate(category_db)
        logger.debug(f"Catégorie avec nom '{name}' non trouvée dans get_by_name().")
        return None

    async def get_by_id(self, category_id: int) -> Optional[Category]:
        """Récupère une catégorie par son ID."""
        stmt = select(models.CategoryDB).where(models.CategoryDB.id == category_id)
        result = await self.session.execute(stmt)
        category_db = result.scalar_one_or_none()
        if category_db:
            return Category.model_validate(category_db)
        return None

    async def list(self, limit: int, offset: int, sort_by: Optional[str], sort_desc: bool, filters: Optional[Dict[str, Any]]) -> Tuple[List[Category], int]:
        """Liste les catégories avec pagination, tri et filtres."""
        # Requête de base pour sélectionner les catégories
        stmt_select = select(models.CategoryDB)
        # Requête de base pour compter le nombre total (avant pagination)
        stmt_count = select(sqlalchemy.func.count(models.CategoryDB.id)).select_from(models.CategoryDB)

        # Appliquer les filtres (inspiré de parse_react_admin_params et crud.list_categories)
        if filters:
            for field, value in filters.items():
                # Gérer le filtre de recherche générique 'q'
                if field == 'q' and value:
                    search_term = f"%{value}%"
                    # Recherche dans le nom et la description
                    filter_condition = (models.CategoryDB.name.ilike(search_term)) | \
                                       (models.CategoryDB.description.ilike(search_term))
                    stmt_select = stmt_select.where(filter_condition)
                    stmt_count = stmt_count.where(filter_condition)
                # Gérer les filtres par ID (souvent une liste)
                elif field == 'id' and isinstance(value, list):
                    if value: # S'assurer que la liste n'est pas vide
                        stmt_select = stmt_select.where(models.CategoryDB.id.in_(value))
                        stmt_count = stmt_count.where(models.CategoryDB.id.in_(value))
                # Gérer les autres filtres par champ exact (si le champ existe)
                elif hasattr(models.CategoryDB, field):
                    column = getattr(models.CategoryDB, field)
                    stmt_select = stmt_select.where(column == value)
                    stmt_count = stmt_count.where(column == value)
                else:
                    logger.warning(f"Filtre ignoré car champ '{field}' inconnu pour CategoryDB.")

        # Appliquer le tri (inspiré de parse_react_admin_params)
        if sort_by and hasattr(models.CategoryDB, sort_by):
            column_to_sort = getattr(models.CategoryDB, sort_by)
            stmt_select = stmt_select.order_by(column_to_sort.desc() if sort_desc else column_to_sort.asc())
        else:
            # Tri par défaut si aucun tri spécifié ou champ invalide
            stmt_select = stmt_select.order_by(models.CategoryDB.id.asc())

        # Exécuter la requête de comptage d'abord
        try:
            total_count_result = await self.session.execute(stmt_count)
            total_count = total_count_result.scalar_one()
        except Exception as e:
            logger.error(f"Erreur SQLAlchemy lors du comptage des catégories: {e}", exc_info=True)
            raise # Propage l'erreur

        # Appliquer la pagination à la requête de sélection
        stmt_select = stmt_select.limit(limit).offset(offset)

        # Exécuter la requête de sélection
        try:
            categories_result = await self.session.execute(stmt_select)
            categories_db = categories_result.scalars().all()

            # Mapper les objets DB en entités Pydantic du domaine
            categories = [Category.model_validate(cat_db) for cat_db in categories_db]
            logger.debug(f"Listage catégories réussi: {len(categories)}/{total_count} retournés.")
            return categories, total_count
        except Exception as e:
            logger.error(f"Erreur SQLAlchemy lors du listage des catégories: {e}", exc_info=True)
            raise # Propage l'erreur

    async def add(self, category_data: Dict[str, Any]) -> Category:
        """Ajoute une nouvelle catégorie."""
        # Vérifier si une catégorie avec le même nom existe déjà
        existing_category = await self.get_by_name(category_data['name'])
        if existing_category:
            raise InvalidOperationException(f"Une catégorie avec le nom '{category_data['name']}' existe déjà.")

        new_category_db = models.CategoryDB(**category_data)
        try:
            self.session.add(new_category_db)
            await self.session.flush() # Valide les contraintes DB et assigne un ID
            await self.session.refresh(new_category_db) # Assure que l'objet est à jour
            logger.info(f"Catégorie '{new_category_db.name}' (ID: {new_category_db.id}) ajoutée avec succès.")
            return Category.model_validate(new_category_db)
        except IntegrityError as e:
             await self.session.rollback() # Annuler la transaction
             logger.error(f"Erreur d'intégrité lors de l'ajout de la catégorie '{category_data['name']}': {e}", exc_info=True)
             # Extraire potentiellement plus d'infos de l'erreur si nécessaire
             raise InvalidOperationException(f"Impossible d'ajouter la catégorie en raison d'une violation de contrainte: {e.orig}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue lors de l'ajout de la catégorie '{category_data['name']}': {e}", exc_info=True)
            raise # Propage une erreur générique

    async def update(self, category_id: int, category_data: Dict[str, Any]) -> Optional[Category]:
        """Met à jour une catégorie existante."""
        if not category_data:
            raise InvalidOperationException("Aucune donnée fournie pour la mise à jour de la catégorie.")

        # Utiliser session.get pour récupérer l'objet par PK (plus efficace)
        category_db = await self.session.get(models.CategoryDB, category_id)
        if not category_db:
             # Conformément à l'interface, retourner None si non trouvé
             # Alternative: raise CategoryNotFoundException(category_id)
             logger.warning(f"Tentative de MAJ catégorie ID {category_id} non trouvée.")
             return None

        # Vérifier la contrainte d'unicité sur le nom si celui-ci est modifié
        new_name = category_data.get('name')
        if new_name and new_name.lower() != category_db.name.lower():
            existing_with_new_name = await self.get_by_name(new_name)
            if existing_with_new_name and existing_with_new_name.id != category_id:
                 raise InvalidOperationException(f"Une autre catégorie (ID: {existing_with_new_name.id}) existe déjà avec le nom '{new_name}'.")

        # Appliquer les mises à jour aux champs autorisés
        updated = False
        for field, value in category_data.items():
            if hasattr(category_db, field):
                # Comparer avant de setter pour éviter flush inutile
                if getattr(category_db, field) != value:
                    setattr(category_db, field, value)
                    updated = True
            else:
                 logger.warning(f"Tentative de mise à jour d'un champ '{field}' inexistant pour Category ID {category_id}")
        
        if not updated:
            logger.info(f"Aucune modification détectée pour la catégorie ID {category_id}. Retour de l'objet existant.")
            return Category.model_validate(category_db) # Retourne l'objet tel quel

        try:
            await self.session.flush() # Applique les changements et vérifie les contraintes
            await self.session.refresh(category_db) # Rafraîchit l'état depuis la DB
            logger.info(f"Catégorie ID {category_id} mise à jour avec succès.")
            return Category.model_validate(category_db)
        except IntegrityError as e:
             await self.session.rollback()
             logger.error(f"Erreur d'intégrité lors de la MAJ catégorie {category_id}: {e}", exc_info=True)
             raise InvalidOperationException(f"Impossible de mettre à jour la catégorie en raison d'une violation de contrainte: {e.orig}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue lors de la MAJ catégorie {category_id}: {e}", exc_info=True)
            raise

    async def delete(self, category_id: int) -> bool:
        """Supprime une catégorie par son ID."""
        # Vérifier si la catégorie existe avant de supprimer
        category_db = await self.session.get(models.CategoryDB, category_id)
        if not category_db:
            logger.warning(f"Tentative de suppression de catégorie ID {category_id}, mais non trouvée.")
            return False # Conforme à l'interface
        
        try:
            await self.session.delete(category_db)
            await self.session.flush() # Appliquer la suppression
            logger.info(f"Catégorie ID {category_id} supprimée avec succès.")
            return True
        except IntegrityError as e:
            # Souvent dû à une contrainte de clé étrangère (ex: produits liés)
            await self.session.rollback()
            logger.error(f"Erreur d'intégrité lors de la suppression de la catégorie {category_id}: {e}", exc_info=True)
            raise InvalidOperationException(f"Impossible de supprimer la catégorie ID {category_id}, elle est probablement utilisée par des produits. Détail: {e.orig}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue lors de la suppression de la catégorie {category_id}: {e}", exc_info=True)
            raise

# --- SQLAlchemyTagRepository ---

class SQLAlchemyTagRepository(AbstractTagRepository):
    """Implémentation SQLAlchemy du repository de Tags."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, tag_id: int) -> Optional[Tag]:
        """Récupère un tag par son ID."""
        logger.debug(f"[Repo Tag] Récupération Tag ID: {tag_id}")
        # Implémenter la logique SQLAlchemy ici (session.get ou select)
        # Exemple:
        # tag_db = await self.session.get(models.TagDB, tag_id)
        # return Tag.model_validate(tag_db) if tag_db else None
        raise NotImplementedError("Méthode get_by_id() non implémentée pour SQLAlchemyTagRepository")

    async def get_by_name(self, name: str) -> Optional[Tag]:
        """Récupère un tag par son nom (insensible à la casse)."""
        stmt = select(models.TagDB).where(func.lower(models.TagDB.name) == name.lower())
        result = await self.session.execute(stmt)
        tag_db = result.scalar_one_or_none()
        return Tag.model_validate(tag_db) if tag_db else None

    async def add(self, tag_data: Dict[str, Any]) -> Tag:
        """Ajoute un nouveau tag."""
        tag_name = tag_data.get('name')
        logger.debug(f"[Repo Tag] Ajout Tag: {tag_name}")
        if not tag_name:
            raise InvalidOperationException("Le nom du tag est requis pour l'ajout.")
            
        # Vérifier l'existence (pourrait lever une exception si dupliqué)
        existing = await self.get_by_name(tag_name)
        if existing:
            raise InvalidOperationException(f"Un tag avec le nom '{tag_name}' existe déjà.")
            
        new_tag_db = models.TagDB(name=tag_name)
        try:
            self.session.add(new_tag_db)
            await self.session.flush()
            await self.session.refresh(new_tag_db)
            logger.info(f"Tag '{new_tag_db.name}' (ID: {new_tag_db.id}) ajouté.")
            return Tag.model_validate(new_tag_db)
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erreur intégrité ajout tag '{tag_name}': {e}", exc_info=True)
            raise InvalidOperationException(f"Impossible d'ajouter le tag: {e.orig}")
        except Exception as e:
             await self.session.rollback()
             logger.error(f"Erreur inattendue ajout tag '{tag_name}': {e}", exc_info=True)
             raise

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Tag]:
        """Liste tous les tags avec pagination."""
        logger.debug(f"[Repo Tag] Listage tags: limit={limit}, offset={offset}")
        stmt = select(models.TagDB).order_by(models.TagDB.id.asc()).limit(limit).offset(offset)
        try:
            result = await self.session.execute(stmt)
            tags_db = result.scalars().all()
            return [Tag.model_validate(tag_db) for tag_db in tags_db]
        except Exception as e:
            logger.error(f"[Repo Tag] Erreur SQLAlchemy listage tags: {e}", exc_info=True)
            raise

# --- SQLAlchemyProductRepository ---

class SQLAlchemyProductRepository(AbstractProductRepository):
    """Implémentation SQLAlchemy du repository de Produits."""

    def __init__(self, session: AsyncSession, tag_repo: AbstractTagRepository):
        self.session = session
        self.tag_repo = tag_repo

    async def get_by_id(self, product_id: int, include_relations: List[str] = []) -> Optional[Product]:
        """Récupère un produit par son ID, incluant ses variantes, tags et catégorie.
        
        Args:
            product_id: L'ID du produit.
            include_relations: (Ignoré pour l'instant) Liste des relations à charger.
        """
        logger.debug(f"[Repo Prod] Récupération Produit ID: {product_id}")
        stmt = select(models.ProductDB).where(models.ProductDB.id == product_id)
        # Eagerly load relationships needed for the Product domain entity
        # Note: Ignoring include_relations for now, always loading standard set
        stmt = stmt.options(
            selectinload(models.ProductDB.category),
            selectinload(models.ProductDB.variants).options(
                selectinload(models.ProductVariantDB.stock),
                selectinload(models.ProductVariantDB.tags)
            )
        )
        try:
            result = await self.session.execute(stmt)
            product_db = result.scalar_one_or_none()

            if not product_db:
                logger.debug(f"Produit ID {product_id} non trouvé dans get_by_id().")
                return None

            # Map to domain entity
            return Product.model_validate(product_db)
        except Exception as e:
            logger.error(f"[Repo Prod] Erreur DB get_by_id Produit ID {product_id}: {e}", exc_info=True)
            raise

    async def list_all(self, 
                       limit: int = 100, 
                       offset: int = 0, 
                       filter_params: Optional[Dict[str, Any]] = None, 
                       include_relations: List[str] = []) -> Tuple[List[Product], int]:
        """Liste les produits avec filtres, pagination et compte total.
        
        Args:
            limit: Nombre max d'items.
            offset: Offset de départ.
            filter_params: Dictionnaire de filtres (ex: {'category_id': 1, 'tag_names': ['tag1'], 'search_term': 'foo'}).
            include_relations: (Ignoré pour l'instant) Liste des relations à charger.
        """
        # Extract specific filters from filter_params for clarity
        category_id = filter_params.get('category_id') if filter_params else None
        tag_names = filter_params.get('tag_names') if filter_params else None
        search_term = filter_params.get('search_term') if filter_params else None
        
        logger.debug(f"[Repo Prod] list_all produits: limit={limit}, offset={offset}, filters={filter_params}")
        
        # Base query for selection with necessary relationships (ignoring include_relations for now)
        stmt_select = select(models.ProductDB).options(
            selectinload(models.ProductDB.category),
            selectinload(models.ProductDB.variants).options(
                selectinload(models.ProductVariantDB.stock),
                selectinload(models.ProductVariantDB.tags)
            )
        )
        stmt_count = select(sqlalchemy.func.count(models.ProductDB.id)).select_from(models.ProductDB)
        
        # --- Apply Filters --- 
        if category_id is not None:
            stmt_select = stmt_select.where(models.ProductDB.category_id == category_id)
            stmt_count = stmt_count.where(models.ProductDB.category_id == category_id)

        if tag_names:
            subquery = select(models.ProductDB.id)\
                .join(models.ProductDB.variants)\
                .join(models.ProductVariantDB.tags)\
                .where(models.TagDB.name.in_(tag_names))\
                .distinct()
            stmt_select = stmt_select.where(models.ProductDB.id.in_(subquery))
            stmt_count = stmt_count.where(models.ProductDB.id.in_(subquery))
            
        if search_term:
            search_pattern = f"%{search_term}%"
            subquery_variants = select(models.ProductVariantDB.product_id)\
                .where(models.ProductVariantDB.sku.ilike(search_pattern))\
                .distinct()
            search_condition = (
                models.ProductDB.name.ilike(search_pattern) |
                models.ProductDB.base_description.ilike(search_pattern) |
                models.ProductDB.id.in_(subquery_variants) 
            )
            stmt_select = stmt_select.where(search_condition)
            stmt_count = stmt_count.where(search_condition)

        # --- Execute Count Query --- 
        try:
            total_count_result = await self.session.execute(stmt_count)
            total_count = total_count_result.scalar_one()
        except Exception as e:
            logger.error(f"[Repo Prod] Erreur SQLAlchemy comptage produits: {e}", exc_info=True)
            raise

        # --- Apply Sorting and Pagination to Select Query --- 
        stmt_select = stmt_select.order_by(models.ProductDB.id.asc()).limit(limit).offset(offset)

        # --- Execute Select Query --- 
        try:
            products_result = await self.session.execute(stmt_select)
            products_db = products_result.unique().scalars().all() 
            products = [Product.model_validate(p_db) for p_db in products_db]
            logger.debug(f"[Repo Prod] list_all produits réussi: {len(products)}/{total_count} retournés.")
            return products, total_count
        except Exception as e:
            logger.error(f"[Repo Prod] Erreur SQLAlchemy list_all produits: {e}", exc_info=True)
            raise

    async def add(self, product_data: Dict[str, Any], tag_names: Optional[List[str]] = None) -> Product:
        """Ajoute un nouveau produit, en associant potentiellement des tags."""
        # Préparer les tags
        tags_db_list = []
        if tag_names:
             # Utiliser le TagRepository (si injecté) ou une logique interne
             # Pour l'instant, logique interne simple
             tag_repo = SQLAlchemyTagRepository(self.session) # Création ad-hoc
             for name in tag_names:
                 tag_db = await tag_repo.get_or_create(name)
                 tags_db_list.append(tag_db) # Attention, on récupère ici l'entité Pydantic
                 # Il faudra peut-être re-mapper vers l'objet DB si on assigne directement
        
        # Créer le produit DB
        new_product_db = models.ProductDB(**product_data)
        # Associer les tags récupérés (objets DB)
        if tags_db_list:
            # Il faut les objets models.TagDB, pas les entités Pydantic
            tag_ids = [t.id for t in tags_db_list]
            stmt_tags = select(models.TagDB).where(models.TagDB.id.in_(tag_ids))
            tags_db_result = await self.session.execute(stmt_tags)
            actual_tags_db = tags_db_result.scalars().all()
            new_product_db.tags.extend(actual_tags_db)

        try:
            self.session.add(new_product_db)
            await self.session.flush()
            # Recharger avec les relations pour retourner l'entité complète
            await self.session.refresh(new_product_db, attribute_names=['category', 'tags']) 
            logger.info(f"Produit '{new_product_db.name}' (ID: {new_product_db.id}) ajouté.")
            # Mapper vers l'entité Pydantic
            return Product.model_validate(new_product_db)
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erreur intégrité ajout produit '{product_data.get('name')}': {e}", exc_info=True)
            raise InvalidOperationException(f"Violation contrainte ajout produit: {e.orig}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue ajout produit '{product_data.get('name')}': {e}", exc_info=True)
            raise

    async def update(self, product_id: int, product_data: Dict[str, Any], tag_names: Optional[List[str]] = None) -> Optional[Product]:
        """Met à jour un produit existant et/ou ses tags."""
        product_db = await self.session.get(models.ProductDB, product_id, options=[selectinload(models.ProductDB.tags)])
        if not product_db:
            logger.warning(f"Tentative MAJ produit ID {product_id} non trouvé.")
            return None
        
        updated = False
        # MAJ champs simples
        for field, value in product_data.items():
            if hasattr(product_db, field) and field != 'tags': # Ne pas écraser les tags ici
                 if getattr(product_db, field) != value:
                    setattr(product_db, field, value)
                    updated = True

        # MAJ Tags (remplacement complet)
        if tag_names is not None:
            tag_repo = SQLAlchemyTagRepository(self.session) # Ad-hoc
            new_tags_db = []
            for name in tag_names:
                tag_db_entity = await tag_repo.get_or_create(name) # Entité pydantic
                # Récupérer l'objet DB correspondant
                tag_db_model = await self.session.get(models.TagDB, tag_db_entity.id)
                if tag_db_model:
                    new_tags_db.append(tag_db_model)
            
            # Comparer les sets d'IDs pour voir si changement
            current_tag_ids = {t.id for t in product_db.tags}
            new_tag_ids = {t.id for t in new_tags_db}
            if current_tag_ids != new_tag_ids:
                product_db.tags = new_tags_db # Remplace la liste des tags associés
                updated = True

        if not updated:
             logger.info(f"Aucune modification détectée pour produit ID {product_id}.")
             # Recharger les relations avant de retourner
             loaded_product = await self.get_by_id(product_id)
             return loaded_product

        try:
            await self.session.flush()
            # Recharger complètement l'entité avec ses relations
            refreshed_product = await self.get_by_id(product_id)
            logger.info(f"Produit ID {product_id} mis à jour.")
            return refreshed_product
        except IntegrityError as e:
             await self.session.rollback()
             logger.error(f"Erreur intégrité MAJ produit {product_id}: {e}", exc_info=True)
             raise InvalidOperationException(f"Violation contrainte MAJ produit: {e.orig}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue MAJ produit {product_id}: {e}", exc_info=True)
            raise

    async def delete(self, product_id: int) -> bool:
        """Supprime un produit par son ID."""
        product_db = await self.session.get(models.ProductDB, product_id)
        if not product_db:
            logger.warning(f"Tentative suppression produit ID {product_id} non trouvé.")
            return False
        
        try:
            # Suppression en cascade (configurée dans les modèles SQLAlchemy) devrait gérer variants/stock/associations
            await self.session.delete(product_db)
            await self.session.flush()
            logger.info(f"Produit ID {product_id} supprimé.")
            return True
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erreur intégrité suppression produit {product_id}: {e}", exc_info=True)
            raise InvalidOperationException(f"Impossible supprimer produit {product_id} (violation contrainte): {e.orig}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue suppression produit {product_id}: {e}", exc_info=True)
            raise

# --- SQLAlchemyProductVariantRepository ---

class SQLAlchemyProductVariantRepository(AbstractProductVariantRepository):
    """Implémentation SQLAlchemy du repository des Variantes de Produit."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_variant_db(self, variant_id: int = None, sku: str = None) -> Optional[models.ProductVariantDB]:
        """Helper interne pour récupérer l'objet DB de la variante par ID ou SKU."""
        stmt = select(models.ProductVariantDB)
        if variant_id:
            stmt = stmt.where(models.ProductVariantDB.id == variant_id)
        elif sku:
            stmt = stmt.where(models.ProductVariantDB.sku == sku)
        else:
            return None # Doit spécifier au moins un critère

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, variant_id: int) -> Optional[ProductVariant]:
        """Récupère une variante par son ID."""
        variant_db = await self._get_variant_db(variant_id=variant_id)
        if variant_db:
            return ProductVariant.model_validate(variant_db)
        logger.warning(f"Variante ID {variant_id} non trouvée.")
        return None

    async def get_by_sku(self, sku: str) -> Optional[ProductVariant]:
        """Récupère une variante par son SKU."""
        variant_db = await self._get_variant_db(sku=sku)
        if variant_db:
            return ProductVariant.model_validate(variant_db)
        logger.debug(f"Variante SKU '{sku}' non trouvée dans get_by_sku().")
        return None

    async def list_for_product(self, product_id: int) -> List[ProductVariant]:
        """Liste toutes les variantes pour un produit donné."""
        stmt = select(models.ProductVariantDB)\
               .where(models.ProductVariantDB.product_id == product_id)\
               .options(selectinload(models.ProductVariantDB.stock))\
               .order_by(models.ProductVariantDB.id)
        result = await self.session.execute(stmt)
        variants_db = result.scalars().all()
        return [ProductVariant.model_validate(v_db) for v_db in variants_db]

    async def add(self, variant_data: Dict[str, Any]) -> ProductVariant:
        """Ajoute une nouvelle variante. Crée aussi l'entrée stock initiale."""
        sku = variant_data.get('sku')
        if not sku:
            raise InvalidOperationException("Le SKU est requis pour créer une variante.")

        # Vérifier l'unicité du SKU
        existing = await self.get_by_sku(sku)
        if existing:
            raise DuplicateSKUException(sku)

        # Vérifier si le produit parent existe
        product_id = variant_data.get('product_id')
        product_exists = await self.session.get(models.ProductDB, product_id)
        if not product_exists:
             raise InvalidOperationException(f"Le produit parent ID {product_id} n'existe pas.")

        new_variant_db = models.ProductVariantDB(**variant_data)
        # Créer l'entrée stock associée avec quantité 0 par défaut
        initial_stock_db = models.StockDB(product_variant=new_variant_db, quantity=0)
        
        try:
            self.session.add(new_variant_db) # Stock sera ajouté par cascade via relation
            await self.session.flush()
            # Recharger avec le stock
            await self.session.refresh(new_variant_db, attribute_names=['stock']) 
            logger.info(f"Variante SKU '{sku}' (ID: {new_variant_db.id}) ajoutée pour produit {product_id}.")
            return ProductVariant.model_validate(new_variant_db)
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erreur intégrité ajout variante SKU '{sku}': {e}", exc_info=True)
            raise InvalidOperationException(f"Violation contrainte ajout variante: {e.orig}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue ajout variante SKU '{sku}': {e}", exc_info=True)
            raise

    async def update(self, variant_id: int, variant_data: Dict[str, Any]) -> Optional[ProductVariant]:
        """Met à jour une variante existante."""
        variant_db = await self.session.get(models.ProductVariantDB, variant_id)
        if not variant_db:
             logger.warning(f"Tentative MAJ variante ID {variant_id} non trouvée.")
             return None
        
        new_sku = variant_data.get('sku')
        if new_sku and new_sku != variant_db.sku:
            # Vérifier unicité nouveau SKU
            existing_with_new_sku = await self.get_by_sku(new_sku)
            if existing_with_new_sku and existing_with_new_sku.id != variant_id:
                raise DuplicateSKUException(new_sku)

        updated = False
        for field, value in variant_data.items():
            if hasattr(variant_db, field):
                if getattr(variant_db, field) != value:
                    setattr(variant_db, field, value)
                    updated = True
            else:
                logger.warning(f"Champ '{field}' ignoré MAJ variante ID {variant_id}.")

        if not updated:
            logger.info(f"Aucune modification détectée variante ID {variant_id}.")
            # Recharger le stock avant de retourner
            await self.session.refresh(variant_db, attribute_names=['stock'])
            return ProductVariant.model_validate(variant_db)

        try:
            await self.session.flush()
            await self.session.refresh(variant_db, attribute_names=['stock'])
            logger.info(f"Variante ID {variant_id} (SKU: {variant_db.sku}) mise à jour.")
            return ProductVariant.model_validate(variant_db)
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erreur intégrité MAJ variante {variant_id}: {e}", exc_info=True)
            raise InvalidOperationException(f"Violation contrainte MAJ variante: {e.orig}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue MAJ variante {variant_id}: {e}", exc_info=True)
            raise

    async def delete(self, variant_id: int) -> bool:
        """Supprime une variante par son ID."""
        variant_db = await self.session.get(models.ProductVariantDB, variant_id)
        if not variant_db:
            logger.warning(f"Tentative suppression variante ID {variant_id} non trouvée.")
            return False
        
        try:
            # La suppression en cascade devrait gérer le stock lié
            await self.session.delete(variant_db)
            await self.session.flush()
            logger.info(f"Variante ID {variant_id} supprimée.")
            return True
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erreur intégrité suppression variante {variant_id}: {e}", exc_info=True)
            raise InvalidOperationException(f"Impossible supprimer variante {variant_id} (violation contrainte): {e.orig}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue suppression variante {variant_id}: {e}", exc_info=True)
            raise

# --- SQLAlchemyStockRepository ---

class SQLAlchemyStockRepository(AbstractStockRepository):
    """Implémentation SQLAlchemy du repository de Stock."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_stock_db(self, variant_id: int) -> Optional[models.StockDB]:
        """Helper pour récupérer l'objet StockDB."""
        # Utiliser session.get est plus direct si la relation est bien configurée
        # Sinon, faire une requête explicite
        stmt = select(models.StockDB).where(models.StockDB.product_variant_id == variant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_variant(self, variant_id: int) -> Optional[Stock]:
        """Récupère le stock pour une variante donnée."""
        stock_db = await self._get_stock_db(variant_id)
        if stock_db:
            return Stock.model_validate(stock_db)
        logger.debug(f"Stock non trouvé pour variante ID {variant_id} dans get_for_variant().")
        return None

    async def get_for_variants(self, variant_ids: List[int]) -> List[Stock]:
        """Récupère les stocks pour une liste de variantes."""
        if not variant_ids:
            return []
        stmt = select(models.StockDB).where(models.StockDB.product_variant_id.in_(variant_ids))
        result = await self.session.execute(stmt)
        stocks_db = result.scalars().all()
        return [Stock.model_validate(s_db) for s_db in stocks_db]

    async def add_or_update(self, variant_id: int, quantity: int) -> Stock:
        """Ajoute ou met à jour l'entrée de stock pour une variante."""
        if quantity < 0:
             raise InvalidOperationException("La quantité de stock ne peut pas être négative.")
             
        stock_db = await self._get_stock_db(variant_id)
        if stock_db:
            # Mise à jour
            stock_db.quantity = quantity
            stock_db.last_updated = datetime.utcnow()
            op_type = "mis à jour"
        else:
            # Vérifier que la variante existe
            variant_exists = await self.session.get(models.ProductVariantDB, variant_id)
            if not variant_exists:
                 raise VariantNotFoundException(variant_id=variant_id)
            # Création
            stock_db = models.StockDB(product_variant_id=variant_id, quantity=quantity)
            self.session.add(stock_db)
            op_type = "ajouté"
        
        try:
            await self.session.flush()
            await self.session.refresh(stock_db)
            logger.info(f"Stock pour variante ID {variant_id} {op_type} à {quantity}.")
            return Stock.model_validate(stock_db)
        except IntegrityError as e:
             await self.session.rollback()
             logger.error(f"Erreur intégrité {op_type} stock variante {variant_id}: {e}", exc_info=True)
             raise InvalidOperationException(f"Violation contrainte {op_type} stock: {e.orig}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue {op_type} stock variante {variant_id}: {e}", exc_info=True)
            raise

    async def update_quantity(self, variant_id: int, quantity_change: int) -> Optional[Stock]:
        """Met à jour la quantité de stock (ajout ou retrait). Retourne le stock mis à jour ou lève une exception."""
        stock_db = await self._get_stock_db(variant_id)
        if not stock_db:
             # Ne peut pas mettre à jour un stock inexistant
             raise StockNotFoundException(variant_id)
        
        new_quantity = stock_db.quantity + quantity_change
        if new_quantity < 0:
            raise InsufficientStockException(variant_id, abs(quantity_change), stock_db.quantity)
            
        stock_db.quantity = new_quantity
        stock_db.last_updated = datetime.utcnow()
        
        try:
            await self.session.flush()
            await self.session.refresh(stock_db)
            logger.info(f"Stock variante {variant_id} ajusté de {quantity_change}. Nouvelle qté: {new_quantity}.")
            return Stock.model_validate(stock_db)
        # Pas besoin de gérer IntegrityError ici normalement, sauf si contrainte CHECK ajoutée
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue MAJ stock variante {variant_id}: {e}", exc_info=True)
            raise
            
    async def set_quantity(self, variant_id: int, new_quantity: int) -> Optional[Stock]:
        """Définit la quantité exacte de stock pour une variante."""
        if new_quantity < 0:
            raise InvalidOperationException("La quantité de stock ne peut pas être négative.")
            
        stock_db = await self._get_stock_db(variant_id)
        if not stock_db:
            raise StockNotFoundException(variant_id)
        
        stock_db.quantity = new_quantity
        stock_db.last_updated = datetime.utcnow()
        
        try:
            await self.session.flush()
            await self.session.refresh(stock_db)
            logger.info(f"Stock variante {variant_id} défini à {new_quantity}.")
            return Stock.model_validate(stock_db)
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue SET stock variante {variant_id}: {e}", exc_info=True)
            raise 

    async def list_low_stock(self, threshold: int, limit: int = 100) -> List[Stock]:
        """Liste les stocks en dessous d'un certain seuil."""
        logger.debug(f"[Repo Stock] Recherche stock < {threshold} (limite: {limit})")
        stmt = select(models.StockDB)\
               .where(models.StockDB.quantity < threshold)\
               .order_by(models.StockDB.quantity.asc(), models.StockDB.product_variant_id.asc())\
               .limit(limit)\
               .options(selectinload(models.StockDB.product_variant)) # Charger la variante pour infos

        try:
            result = await self.session.execute(stmt)
            stocks_db = result.scalars().all()
            # Mapper vers entités domaine
            low_stocks = [Stock.model_validate(s_db) for s_db in stocks_db]
            logger.debug(f"Trouvé {len(low_stocks)} stocks bas.")
            return low_stocks
        except Exception as e:
            logger.error(f"Erreur SQLAlchemy listage stock bas (< {threshold}): {e}", exc_info=True)
            raise