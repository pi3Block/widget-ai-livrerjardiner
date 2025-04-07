import logging
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal

# Repositories (Interfaces)
from src.products.domain.repositories import (
    AbstractProductRepository,
    AbstractCategoryRepository,
    AbstractTagRepository,
    AbstractProductVariantRepository,
    AbstractStockRepository
)

# Entités du Domaine
from src.products.domain.entities import Product, Category, Tag, ProductVariant, Stock

# Schémas/DTOs de l'Application
from .schemas import (
    ProductCreate, ProductUpdate, ProductResponse, 
    CategoryCreate, CategoryUpdate, CategoryResponse,
    TagCreate, TagResponse, 
    ProductVariantCreate, ProductVariantUpdate, ProductVariantResponse,
    StockUpdate, StockResponse,
    PaginatedProductResponse, PaginatedCategoryResponse, PaginatedTagResponse, PaginatedVariantResponse
)

# Exceptions du Domaine
from src.products.domain.exceptions import (
    ProductNotFoundException, CategoryNotFoundException, TagNotFoundException,
    VariantNotFoundException, StockNotFoundException, InsufficientStockException,
    InvalidOperationException, ProductUpdateFailedException, ProductCreationFailedException
)

logger = logging.getLogger(__name__)

class ProductService:
    """Service applicatif pour la gestion complète du catalogue produits."""

    def __init__(self, 
                 product_repo: AbstractProductRepository,
                 category_repo: AbstractCategoryRepository,
                 tag_repo: AbstractTagRepository,
                 variant_repo: AbstractProductVariantRepository,
                 stock_repo: AbstractStockRepository):
        self.product_repo = product_repo
        self.category_repo = category_repo
        self.tag_repo = tag_repo
        self.variant_repo = variant_repo
        self.stock_repo = stock_repo

    # --- Méthodes pour Produits --- 

    async def get_product(self, product_id: int, include_relations: List[str] = ['variants', 'category', 'tags']) -> Optional[ProductResponse]:
        """Récupère un produit par ID, incluant ses relations par défaut."""
        logger.debug(f"[ProductService] Récupération produit ID: {product_id} avec relations: {include_relations}")
        product_entity = await self.product_repo.get_by_id(product_id, include_relations)
        if not product_entity:
            return None
        
        # Charger explicitement le stock pour chaque variante si demandé
        if 'variants' in include_relations:
            for variant in product_entity.variants:
                stock_info = await self.stock_repo.get_for_variant(variant.id)
                if stock_info:
                    # Injecter le StockResponse dans le ProductVariantResponse
                    variant_response = next((vr for vr in ProductResponse.model_validate(product_entity).variants if vr.id == variant.id), None)
                    if variant_response:
                         variant_response.stock = StockResponse.model_validate(stock_info)
        
        return ProductResponse.model_validate(product_entity)

    async def list_products(
        self, 
        limit: int, 
        offset: int, 
        category_id: Optional[int] = None,
        tag_names: Optional[List[str]] = None,
        search_term: Optional[str] = None,
        include_relations: List[str] = []
    ) -> PaginatedProductResponse:
        """Liste les produits avec filtres spécifiques, pagination et chargement de relations."""
        # Construire les filtres pour le repo à partir des paramètres
        repo_filters = {}
        if category_id is not None:
            repo_filters['category_id'] = category_id
        if tag_names:
            repo_filters['tag_names'] = tag_names # Le repo devra gérer ce filtre
        if search_term:
            repo_filters['search_term'] = search_term # Le repo devra gérer ce filtre
        # Ajouter d'autres filtres si nécessaire depuis l'ancien filter_params

        logger.debug(f"[ProductService] Listage produits, limit={limit}, offset={offset}, filters={repo_filters}, include={include_relations}")
        
        product_entities, total_count = await self.product_repo.list_all(limit, offset, repo_filters, include_relations)
        product_responses = [ProductResponse.model_validate(p) for p in product_entities]
        
        # Charger le stock pour les variantes si demandé implicitement par la réponse
        # (Peut être optimisé avec un appel groupé au repo stock)
        if product_responses:
             variant_ids = [var.id for prod in product_responses for var in prod.variants]
             if variant_ids:
                  # TODO: Ajouter une méthode list_for_variants au repo stock
                  logger.warning("[ProductService] Chargement individuel du stock pour les variantes listées. A optimiser.")
                  for prod_resp in product_responses:
                       for var_resp in prod_resp.variants:
                           stock_info = await self.stock_repo.get_for_variant(var_resp.id)
                           if stock_info:
                                var_resp.stock = StockResponse.model_validate(stock_info)
                                
        return PaginatedProductResponse(items=product_responses, total=total_count)

    async def create_product(self, product_data: ProductCreate) -> ProductResponse:
        """Crée un nouveau produit."""
        logger.info(f"[ProductService] Tentative création produit: {product_data.name}")
        # Valider la catégorie
        category = await self.category_repo.get_by_id(product_data.category_id)
        if not category:
            raise CategoryNotFoundException(product_data.category_id)
        
        # Valider les tags (si fournis)
        if product_data.tag_ids:
             # TODO: Valider que tous les tag_ids existent (via repo tag list_by_ids ?)
             pass 
        
        try:
            product_dict = product_data.model_dump(exclude={'tag_ids'})
            created_product_entity = await self.product_repo.add(product_dict, product_data.tag_ids)
            logger.info(f"[ProductService] Produit ID {created_product_entity.id} créé.")
            # Recharger avec les relations pour la réponse
            full_product = await self.get_product(created_product_entity.id)
            if not full_product:
                 raise ProductCreationFailedException("Erreur rechargement produit après création.")
            return full_product
        except Exception as e:
            logger.error(f"[ProductService] Erreur création produit {product_data.name}: {e}", exc_info=True)
            raise ProductCreationFailedException(f"Erreur interne création produit: {e}")
            
    async def update_product(self, product_id: int, product_data: ProductUpdate) -> Optional[ProductResponse]:
        """Met à jour un produit existant."""
        logger.info(f"[ProductService] Tentative MAJ produit ID: {product_id}")
        # Valider que le produit existe
        existing_product = await self.product_repo.get_by_id(product_id)
        if not existing_product:
            raise ProductNotFoundException(product_id)
            
        # Valider la catégorie si modifiée
        if product_data.category_id is not None and product_data.category_id != existing_product.category_id:
            category = await self.category_repo.get_by_id(product_data.category_id)
            if not category:
                raise CategoryNotFoundException(product_data.category_id)
                
        # Valider les tags si modifiés
        if product_data.tag_ids is not None:
            # TODO: Valider que tous les tag_ids existent
            pass
            
        try:
            update_dict = product_data.model_dump(exclude={'tag_ids'}, exclude_unset=True)
            updated_product_entity = await self.product_repo.update(product_id, update_dict, product_data.tag_ids)
            if not updated_product_entity:
                 # L'update a pu échouer silencieusement dans le repo ou le produit a été supprimé entre temps
                 raise ProductUpdateFailedException(f"La mise à jour du produit {product_id} a échoué.")
                 
            logger.info(f"[ProductService] Produit ID {product_id} mis à jour.")
            # Recharger avec les relations
            full_product = await self.get_product(updated_product_entity.id)
            if not full_product:
                raise ProductUpdateFailedException("Erreur rechargement produit après MAJ.")
            return full_product
        except Exception as e:
            logger.error(f"[ProductService] Erreur MAJ produit {product_id}: {e}", exc_info=True)
            raise ProductUpdateFailedException(f"Erreur interne MAJ produit: {e}")

    # --- Méthodes pour Variantes --- 

    async def get_variant(self, variant_id: int) -> Optional[ProductVariantResponse]:
        """Récupère une variante par ID, incluant son stock."""
        logger.debug(f"[ProductService] Récupération variante ID: {variant_id}")
        variant_entity = await self.variant_repo.get_by_id(variant_id)
        if not variant_entity:
            return None
        
        variant_response = ProductVariantResponse.model_validate(variant_entity)
        stock_info = await self.stock_repo.get_for_variant(variant_id)
        if stock_info:
            variant_response.stock = StockResponse.model_validate(stock_info)
            
        return variant_response
        
    async def list_variants_for_product(self, product_id: int, limit: int = 50, offset: int = 0) -> PaginatedVariantResponse:
        """Liste les variantes d'un produit avec leur stock."""
        logger.debug(f"[ProductService] Listage variantes pour produit ID: {product_id}")
        # Vérifier que le produit existe
        product_exists = await self.product_repo.get_by_id(product_id, include_relations=[])
        if not product_exists:
            raise ProductNotFoundException(product_id)
            
        variant_entities = await self.variant_repo.list_for_product(product_id, limit, offset)
        # TODO: Compter le total via repo variant
        total_count = len(variant_entities)
        logger.warning(f"[ProductService] Pagination variantes pour produit {product_id} approximative.")
        
        variant_responses = []
        if variant_entities:
            # Charger le stock (optimisable)
            logger.warning("[ProductService] Chargement individuel du stock pour les variantes listées. A optimiser.")
            for variant in variant_entities:
                 variant_resp = ProductVariantResponse.model_validate(variant)
                 stock_info = await self.stock_repo.get_for_variant(variant.id)
                 if stock_info:
                      variant_resp.stock = StockResponse.model_validate(stock_info)
                 variant_responses.append(variant_resp)
                 
        return PaginatedVariantResponse(items=variant_responses, total=total_count)
        
    async def create_variant(self, variant_data: ProductVariantCreate) -> ProductVariantResponse:
        """Crée une nouvelle variante pour un produit et initialise son stock."""
        logger.info(f"[ProductService] Tentative création variante SKU: {variant_data.sku} pour produit ID: {variant_data.product_id}")
        # Valider que le produit parent existe
        product = await self.product_repo.get_by_id(variant_data.product_id, include_relations=[])
        if not product:
            raise ProductNotFoundException(variant_data.product_id)
            
        # Vérifier unicité SKU (peut être géré par contrainte DB aussi)
        existing_variant = await self.variant_repo.get_by_sku(variant_data.sku)
        if existing_variant:
            raise InvalidOperationException(f"Le SKU '{variant_data.sku}' existe déjà.")
            
        try:
            variant_dict = variant_data.model_dump(exclude={'initial_stock'})
            created_variant_entity = await self.variant_repo.add(variant_dict)
            logger.info(f"[ProductService] Variante ID {created_variant_entity.id} créée.")
            
            # Initialiser le stock
            stock_data = {
                "product_variant_id": created_variant_entity.id,
                "quantity": variant_data.initial_stock or 0,
                # "location": "default" # Ou laisser None
            }
            await self.stock_repo.add_or_update(stock_data)
            logger.info(f"[ProductService] Stock initialisé pour variante ID {created_variant_entity.id} à {stock_data['quantity']}.")
            
            # Recharger la variante avec le stock pour la réponse
            return await self.get_variant(created_variant_entity.id)
            
        except Exception as e:
            # TODO: Gérer le rollback potentiel si la création variante réussit mais le stock échoue
            logger.error(f"[ProductService] Erreur création variante SKU {variant_data.sku}: {e}", exc_info=True)
            raise InvalidOperationException(f"Erreur interne création variante: {e}")
            
    async def update_variant(self, variant_id: int, variant_data: ProductVariantUpdate) -> Optional[ProductVariantResponse]:
        """Met à jour une variante existante."""
        logger.info(f"[ProductService] Tentative MAJ variante ID: {variant_id}")
        # Valider que la variante existe
        existing_variant = await self.variant_repo.get_by_id(variant_id)
        if not existing_variant:
            raise VariantNotFoundException(variant_id=variant_id)
            
        # Vérifier unicité SKU si modifié
        if variant_data.sku is not None and variant_data.sku != existing_variant.sku:
            other_variant = await self.variant_repo.get_by_sku(variant_data.sku)
            if other_variant and other_variant.id != variant_id:
                 raise InvalidOperationException(f"Le SKU '{variant_data.sku}' existe déjà pour une autre variante.")
                 
        try:
            update_dict = variant_data.model_dump(exclude_unset=True)
            updated_variant_entity = await self.variant_repo.update(variant_id, update_dict)
            if not updated_variant_entity:
                 raise InvalidOperationException(f"La mise à jour de la variante {variant_id} a échoué.")
                 
            logger.info(f"[ProductService] Variante ID {variant_id} mise à jour.")
            # Recharger avec stock
            return await self.get_variant(updated_variant_entity.id)
            
        except Exception as e:
            logger.error(f"[ProductService] Erreur MAJ variante {variant_id}: {e}", exc_info=True)
            raise InvalidOperationException(f"Erreur interne MAJ variante: {e}")
            
    # --- Méthodes pour Stock --- 
    
    async def get_stock_for_variant(self, variant_id: int) -> Optional[StockResponse]:
        """Récupère le stock d'une variante."""
        logger.debug(f"[ProductService] Récupération stock pour variante ID: {variant_id}")
        stock_info = await self.stock_repo.get_for_variant(variant_id)
        if not stock_info:
             # Décision: retourner 404 ou un stock de 0 ? Pour l'instant 404 implicite (None)
             logger.warning(f"[ProductService] Info stock non trouvée pour variante ID: {variant_id}")
             return None
        return StockResponse.model_validate(stock_info)
        
    async def update_stock_quantity(self, variant_id: int, quantity_update: StockUpdate) -> Optional[StockResponse]:
        """Met à jour la quantité de stock (remplace la valeur existante)."""
        logger.info(f"[ProductService] Tentative MAJ stock pour variante ID: {variant_id} à quantité: {quantity_update.quantity}")
        # Valider que la variante existe (optionnel, mais peut éviter des erreurs stock orphelin)
        variant_exists = await self.variant_repo.get_by_id(variant_id)
        if not variant_exists:
            raise VariantNotFoundException(variant_id=variant_id)
            
        try:
             stock_data = {
                 "product_variant_id": variant_id,
                 "quantity": quantity_update.quantity,
                 "location": quantity_update.location
                 # last_updated sera géré par le repo ou la DB
             }
             updated_stock = await self.stock_repo.add_or_update(stock_data)
             logger.info(f"[ProductService] Stock mis à jour pour variante ID {variant_id}.")
             return StockResponse.model_validate(updated_stock)
        except Exception as e:
            logger.error(f"[ProductService] Erreur MAJ stock variante {variant_id}: {e}", exc_info=True)
            raise InvalidOperationException(f"Erreur interne MAJ stock: {e}")
            
    # --- Méthodes pour Catégories --- 
    # (Ajout de la méthode manquante get_category)
    async def get_category(self, category_id: int) -> Optional[CategoryResponse]:
        """Récupère une catégorie par son ID."""
        logger.debug(f"[ProductService] Récupération catégorie ID: {category_id}")
        category_entity = await self.category_repo.get_by_id(category_id)
        if not category_entity:
            return None
        return CategoryResponse.model_validate(category_entity)

    async def list_categories(self, limit: int = 100, offset: int = 0, sort_by: Optional[str] = None, sort_desc: bool = False, filters: Optional[Dict[str, Any]] = None) -> PaginatedCategoryResponse:
         """Liste les catégories avec filtres, tri et pagination."""
         logger.debug(f"[ProductService] Listage catégories: limit={limit}, offset={offset}, sort_by={sort_by}, sort_desc={sort_desc}, filters={filters}")
         
         # Passer tous les arguments au repository
         categories, total_count = await self.category_repo.list(
             limit=limit, 
             offset=offset, 
             sort_by=sort_by, 
             sort_desc=sort_desc, 
             filters=filters
         )
         
         # Utiliser le total_count retourné par le repository
         return PaginatedCategoryResponse(items=[CategoryResponse.model_validate(c) for c in categories], total=total_count)
         
    async def create_category(self, category_data: CategoryCreate) -> CategoryResponse:
         logger.info(f"[ProductService] Tentative création catégorie: {category_data.name}")
         # TODO: Valider parent_id si fourni
         created_category = await self.category_repo.add(category_data.model_dump())
         return CategoryResponse.model_validate(created_category)
         
    # --- Méthodes pour Tags --- (Simplifié pour l'instant)
    
    async def list_tags(self, limit: int = 100, offset: int = 0) -> PaginatedTagResponse:
         logger.debug("[ProductService] Listage tags.")
         tags = await self.tag_repo.list_all(limit, offset)
         # TODO: Compter total via repo
         return PaginatedTagResponse(items=[TagResponse.model_validate(t) for t in tags], total=len(tags))
         
    async def create_tag(self, tag_data: TagCreate) -> TagResponse:
         logger.info(f"[ProductService] Tentative création tag: {tag_data.name}")
         # Vérifier si le tag existe déjà ? Le repo pourrait le faire (get_or_create)
         created_tag = await self.tag_repo.add(tag_data.model_dump())
         return TagResponse.model_validate(created_tag)

# Ajouter ici ProductService, StockService etc. 