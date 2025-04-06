import logging
from typing import Optional, List, Annotated, Dict, Any, Tuple
import json # Pour parser les filtres/sorties potentiels de React-Admin

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body, Response, Request

# Services Applicatifs (via dépendances)
from .dependencies import ProductServiceDep, get_product_service

# Schémas/DTOs
from src.products.application.schemas import (
    ProductResponse, ProductCreate, ProductUpdate, PaginatedProductResponse,
    CategoryResponse, CategoryCreate, CategoryUpdate, PaginatedCategoryResponse,
    ProductVariantResponse, ProductVariantCreate, ProductVariantUpdate, 
    StockResponse, StockUpdate, TagCreate, TagResponse, PaginatedTagResponse
)

# Exceptions du Domaine (pour un éventuel mapping fin)
from src.products.domain.exceptions import (
    ProductNotFoundException, CategoryNotFoundException, VariantNotFoundException, 
    DuplicateSKUException, InvalidOperationException, InsufficientStockException,
    TagNotFoundException, StockNotFoundException, ProductUpdateFailedException, ProductCreationFailedException
)

# Dépendances d'Authentification (ajuster l'import si nécessaire)
from src.core.security import get_current_admin_user_entity, get_current_active_user_entity
from src.users.domain.user_entity import UserEntity # Pour typer current_admin_user
from src.database import models # <-- Mise à jour de l'import

logger = logging.getLogger(__name__)

# Alias pour dépendances Auth
CurrentUser = Annotated[UserEntity, Depends(get_current_active_user_entity)] # Corrected type and dependency
CurrentAdmin = Annotated[UserEntity, Depends(get_current_admin_user_entity)] # Corrected type and dependency

# --- Création du Routeur --- 
# On peut créer plusieurs routeurs si nécessaire (ex: un pour /products, un pour /categories)
# Ou regrouper sous un préfixe commun.
product_router = APIRouter(
    # prefix="/catalog", # Ou garder des préfixes séparés comme avant
    tags=["Products & Catalog"] # Tag commun pour Swagger UI
)

# --- Helper pour les paramètres React-Admin (si nécessaire) ---
# Gardé de l'ancien main.py pour compatibilité potentielle, mais les endpoints utiliseront des params standards par défaut.
def parse_react_admin_params(
    request: Request,
    filter: Optional[str] = Query(None), 
    range: Optional[str] = Query(None),  
    sort: Optional[str] = Query(None)    
) -> Tuple[int, int, Optional[str], bool, Optional[Dict[str, Any]]]:
    """Parse les query params spécifiques à React-Admin (filter, range, sort)."""
    offset = 0
    limit = 100 
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
        except json.JSONDecodeError:
            logger.warning(f"Paramètre 'filter' n'est pas du JSON valide: {filter}. Pas de filtres appliqués.")
            filters = None
    
    return limit, offset, sort_by, sort_desc, filters

AdminDep = Annotated[UserEntity, Depends(get_current_admin_user_entity)]

# --- Endpoints pour les Catégories ---

@product_router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    response: Response,
    product_service: ProductServiceDep, # Changed from CategoryServiceDep
    # Utilisation des paramètres React-Admin via la dépendance helper
    params: Tuple[int, int, Optional[str], bool, Optional[Dict[str, Any]]] = Depends(parse_react_admin_params),
):
    """Liste les catégories (compatible React-Admin)."""
    limit, offset, sort_by, sort_desc, filters = params
    logger.info(f"API list_categories: limit={limit}, offset={offset}, sort={sort_by}, desc={sort_desc}, filters={filters}")
    try:
        # Changed from category_service to product_service
        categories, total_count = await product_service.list_categories( 
            limit=limit, offset=offset, sort_by=sort_by, sort_desc=sort_desc, filters=filters
        )
        # Header Content-Range pour React-Admin
        end_range = offset + len(categories) - 1 if categories else offset
        response.headers["Content-Range"] = f"categories {offset}-{end_range}/{total_count}"
        return categories
    except Exception as e:
        logger.error(f"Erreur API list_categories: {e}", exc_info=True)
        # Idéalement, utiliser un exception handler global
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lors du listage des catégories.")

@product_router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    product_service: ProductServiceDep, # Reordered: Non-default first
    category_id: int = Path(..., title="ID de la catégorie", ge=1)
):
    """Récupère une catégorie par son ID."""
    logger.info(f"API get_category: ID={category_id}")
    # Changed from category_service to product_service
    category = await product_service.get_category(category_id) 
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie non trouvée")
    return category

@product_router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    product_service: ProductServiceDep, # Reordered: Non-default first
    current_admin_user: AdminDep, # Reordered: Non-default first
    category_in: CategoryCreate
):
    """Crée une nouvelle catégorie (Admin requis)."""
    logger.info(f"API create_category par admin {current_admin_user.id}: name={category_in.name}")
    try:
        # Changed from category_service to product_service
        created_category = await product_service.create_category(category_in) 
        return created_category
    except InvalidOperationException as e:
        logger.warning(f"Erreur validation création catégorie: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API create_category: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne création catégorie.")

@product_router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    product_service: ProductServiceDep, # Reordered: Non-default first
    current_admin_user: AdminDep, # Reordered: Non-default first
    category_id: int = Path(..., title="ID de la catégorie à MAJ", ge=1),
    category_in: CategoryUpdate = Body(...)
):
    """Met à jour une catégorie (Admin requis)."""
    logger.info(f"API update_category par admin {current_admin_user.id}: ID={category_id}")
    try:
        # Changed from category_service to product_service
        updated_category = await product_service.update_category(category_id, category_in) 
        if not updated_category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie non trouvée")
        return updated_category
    except InvalidOperationException as e:
        logger.warning(f"Erreur validation MAJ catégorie {category_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API update_category {category_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne MAJ catégorie.")

@product_router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    product_service: ProductServiceDep, # Reordered: Non-default first
    current_admin_user: AdminDep, # Reordered: Non-default first
    category_id: int = Path(..., title="ID de la catégorie à supprimer", ge=1)
):
    """Supprime une catégorie (Admin requis)."""
    logger.info(f"API delete_category par admin {current_admin_user.id}: ID={category_id}")
    try:
        # Changed from category_service to product_service
        deleted = await product_service.delete_category(category_id) 
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie non trouvée")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except InvalidOperationException as e:
         # Ex: Impossible de supprimer car utilisée
        logger.warning(f"Erreur suppression catégorie {category_id}: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API delete_category {category_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne suppression catégorie.")


# --- Endpoints pour les Produits ---

@product_router.get("/products", response_model=List[ProductResponse])
async def list_products(
    response: Response,
    product_service: ProductServiceDep,
    # Paramètres standards de pagination/filtrage
    limit: int = Query(100, ge=1, le=1000, description="Nombre max de produits à retourner"),
    offset: int = Query(0, ge=0, description="Nombre de produits à sauter"),
    category_id: Optional[int] = Query(None, description="Filtrer par ID de catégorie"),
    tags: Optional[str] = Query(None, description="Filtrer par tags (séparés par virgule)"),
    q: Optional[str] = Query(None, alias="search_term", description="Terme de recherche (nom, description, SKU)") 
):
    """Liste les produits avec filtres et pagination standards."""
    logger.info(f"API list_products: limit={limit}, offset={offset}, cat={category_id}, tags={tags}, q={q}")
    tag_names_list = tags.split(',') if tags else None
    if tag_names_list:
        tag_names_list = [tag.strip() for tag in tag_names_list if tag.strip()]
        
    try:
        paginated_result = await product_service.list_products(
            limit=limit, offset=offset, category_id=category_id, tag_names=tag_names_list, search_term=q
        )
        # Header Content-Range pour compatibilité
        end_range = offset + len(paginated_result.items) - 1 if paginated_result.items else offset
        response.headers["Content-Range"] = f"products {offset}-{end_range}/{paginated_result.total}"
        return paginated_result.items
    except Exception as e:
        logger.error(f"Erreur API list_products: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne listage produits.")

@product_router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_service: ProductServiceDep, # Reordered: Non-default first
    product_id: int = Path(..., title="ID du produit", ge=1)
):
    """Récupère un produit spécifique par son ID."""
    logger.info(f"API get_product: ID={product_id}")
    product = await product_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit non trouvé")
    return product

@product_router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_service: ProductServiceDep, # Reordered: Non-default first
    current_admin_user: AdminDep, # Reordered: Non-default first
    product_in: ProductCreate
):
    """Crée un nouveau produit (Admin requis)."""
    logger.info(f"API create_product par admin {current_admin_user.id}: name={product_in.name}")
    try:
        created_product = await product_service.create_product(product_in)
        return created_product
    except InvalidOperationException as e:
        logger.warning(f"Erreur validation création produit: {e}")
        # Catégorie non trouvée ou autre violation de règle métier
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API create_product: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne création produit.")

@product_router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_service: ProductServiceDep, # Reordered: Non-default first
    current_admin_user: AdminDep, # Reordered: Non-default first
    product_id: int = Path(..., title="ID du produit à MAJ", ge=1),
    product_in: ProductUpdate = Body(...)
):
    """Met à jour un produit (Admin requis)."""
    logger.info(f"API update_product par admin {current_admin_user.id}: ID={product_id}")
    try:
        updated_product = await product_service.update_product(product_id, product_in)
        if not updated_product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit non trouvé")
        return updated_product
    except InvalidOperationException as e:
        logger.warning(f"Erreur validation MAJ produit {product_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API update_product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne MAJ produit.")

@product_router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_service: ProductServiceDep, # Reordered: Non-default first
    current_admin_user: AdminDep, # Reordered: Non-default first
    product_id: int = Path(..., title="ID du produit à supprimer", ge=1)
):
    """Supprime un produit (Admin requis)."""
    logger.info(f"API delete_product par admin {current_admin_user.id}: ID={product_id}")
    try:
        deleted = await product_service.delete_product(product_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit non trouvé")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except InvalidOperationException as e:
        logger.warning(f"Erreur suppression produit {product_id}: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API delete_product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne suppression produit.")

# --- Endpoints pour les Variantes Produit ---
# On préfixe avec /products/{product_id} ou on utilise un préfixe /variants ?
# Option 1: /products/{product_id}/variants

@product_router.post("/products/{product_id}/variants", response_model=ProductVariantResponse, status_code=status.HTTP_201_CREATED)
async def create_variant_for_product(
    product_service: ProductServiceDep, # Reordered: Non-default first
    current_admin_user: AdminDep, # Reordered: Non-default first
    product_id: int = Path(..., title="ID du produit parent", ge=1),
    variant_in: ProductVariantCreate = Body(...)
):
    """Crée une nouvelle variante pour un produit spécifique (Admin requis)."""
    logger.info(f"API create_variant par admin {current_admin_user.id} pour produit {product_id}, SKU: {variant_in.sku}")
    # Assurer la cohérence de l'ID produit
    if variant_in.product_id != product_id:
        logger.warning(f"Incohérence ID produit dans create_variant: Path={product_id}, Body={variant_in.product_id}. Utilisation Path.")
        variant_in.product_id = product_id
        
    try:
        created_variant = await product_service.create_variant(variant_in)
        return created_variant
    except (InvalidOperationException, DuplicateSKUException) as e:
        logger.warning(f"Erreur validation création variante pour produit {product_id}: {e}")
        # Produit non trouvé, SKU dupliqué, etc.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API create_variant pour produit {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne création variante.")

@product_router.get("/products/{product_id}/variants", response_model=List[ProductVariantResponse])
async def list_variants_for_product(
    product_service: ProductServiceDep, # Reordered: Non-default first
    product_id: int = Path(..., title="ID du produit", ge=1)
):
    """Liste toutes les variantes pour un produit spécifique."""
    logger.info(f"API list_variants pour produit ID: {product_id}")
    try:
        variants = await product_service.list_variants_for_product(product_id)
        return variants
    except ProductNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API list_variants pour produit {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne listage variantes.")

# Option 2: Endpoints séparés pour /variants/{variant_id}
# Cela peut être plus RESTful pour accéder/modifier une variante spécifique

@product_router.get("/variants/{variant_id}", response_model=ProductVariantResponse)
async def get_variant(
    product_service: ProductServiceDep, # Reordered: Non-default first
    variant_id: int = Path(..., title="ID de la variante", ge=1)
):
    """Récupère une variante spécifique par son ID."""
    logger.info(f"API get_variant: ID={variant_id}")
    variant = await product_service.get_variant(variant_id)
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variante non trouvée")
    return variant

@product_router.put("/variants/{variant_id}", response_model=ProductVariantResponse)
async def update_variant(
    product_service: ProductServiceDep, # Reordered: Non-default first
    current_admin_user: AdminDep, # Reordered: Non-default first
    variant_id: int = Path(..., title="ID de la variante à MAJ", ge=1),
    variant_in: ProductVariantUpdate = Body(...)
):
    """Met à jour une variante spécifique (Admin requis)."""
    logger.info(f"API update_variant par admin {current_admin_user.id}: ID={variant_id}")
    try:
        updated_variant = await product_service.update_variant(variant_id, variant_in)
        if not updated_variant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variante non trouvée")
        return updated_variant
    except (InvalidOperationException, DuplicateSKUException) as e:
        logger.warning(f"Erreur validation MAJ variante {variant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API update_variant {variant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne MAJ variante.")

@product_router.delete("/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variant(
    product_service: ProductServiceDep, # Reordered: Non-default first
    current_admin_user: AdminDep, # Reordered: Non-default first
    variant_id: int = Path(..., title="ID de la variante à supprimer", ge=1)
):
    """Supprime une variante spécifique (Admin requis)."""
    logger.info(f"API delete_variant par admin {current_admin_user.id}: ID={variant_id}")
    try:
        deleted = await product_service.delete_variant(variant_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variante non trouvée")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except InvalidOperationException as e:
        logger.warning(f"Erreur suppression variante {variant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API delete_variant {variant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne suppression variante.")

# --- Endpoints pour le Stock --- 
# Associé aux variantes

@product_router.put("/variants/{variant_id}/stock", response_model=StockResponse)
async def update_variant_stock(
    product_service: ProductServiceDep, # Reordered: Non-default first
    current_admin_user: AdminDep, # Reordered: Non-default first
    variant_id: int = Path(..., title="ID de la variante dont on MAJ le stock", ge=1),
    stock_in: StockUpdate = Body(...)
):
    """Met à jour (définit) la quantité de stock pour une variante (Admin requis)."""
    logger.info(f"API update_variant_stock par admin {current_admin_user.id}: VariantID={variant_id}, Qté={stock_in.quantity}")
    try:
        updated_stock = await product_service.update_stock_for_variant(variant_id, stock_in)
        return updated_stock
    except VariantNotFoundException as e:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidOperationException as e:
        logger.warning(f"Erreur validation MAJ stock pour variante {variant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API update_variant_stock {variant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne MAJ stock.")

# On pourrait ajouter un GET /variants/{variant_id}/stock si besoin
# GET /variants/sku/{sku} ? Utile ?
@product_router.get("/variants/sku/{sku}", response_model=ProductVariantResponse)
async def get_variant_by_sku(
    product_service: ProductServiceDep, # Reordered: Non-default first
    sku: str = Path(..., title="SKU de la variante")
):
    """Récupère une variante spécifique par son SKU."""
    logger.info(f"API get_variant_by_sku: SKU={sku}")
    variant = await product_service.get_variant_by_sku(sku)
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Variante avec SKU '{sku}' non trouvée")
    return variant

# --- Routeur pour le Stock (séparé ou sous-routeur?) ---
# Peut être utile pour ajustements manuels par admin

stock_router = APIRouter(
    prefix="/stock",
    tags=["Stock"],
    dependencies=[Depends(get_current_admin_user_entity)] # Protéger toutes les routes stock
)

@stock_router.get("/variants/{variant_id}", response_model=StockResponse)
async def get_stock_endpoint(
    service: ProductServiceDep, # Reordered: Non-default first
    variant_id: int = Path(..., ge=1)
):
    """Récupère le niveau de stock pour une variante spécifique."""
    try:
        stock = await service.get_stock_for_variant(variant_id)
        if stock is None:
             # Lever 404 si la variante n'existe pas OU si le stock n'a jamais été initialisé?
             # Le service retourne None si StockDB n'existe pas. Vérifier la variante avant?
             variant_check = await service.get_variant(variant_id)
             if not variant_check:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Variante ID {variant_id} non trouvée.")
             else:
                 # Variante existe mais pas de StockDB -> Erreur ou stock 0 implicite?
                 # Ici on retourne 404 car l'entrée StockDB devrait exister.
                  raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Information de stock non trouvée pour variante ID {variant_id}.")
        return stock
    except VariantNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur récupération stock variante {variant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

@stock_router.put("/variants/{variant_id}", response_model=StockResponse)
async def update_stock_endpoint(
    service: ProductServiceDep, # Non-default
    stock_data: StockUpdate,    # Non-default (Body)
    variant_id: int = Path(..., ge=1) # Default (Path)
):
    """Met à jour (remplace) la quantité de stock pour une variante."""
    try:
        updated_stock = await service.update_stock_quantity(variant_id=variant_id, quantity_update=stock_data)
        if updated_stock is None:
             # Peut arriver si la variante n'existe pas
              raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Variante ID {variant_id} non trouvée pour mise à jour du stock.")
        return updated_stock
    except VariantNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidOperationException as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur MAJ stock variante {variant_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

# --- Routeurs pour Catégories et Tags (séparés) ---

category_router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
    # Sécurité: Lecture publique, Écriture admin?
)

tags_router = APIRouter(
    prefix="/tags",
    tags=["Tags"]
    # Sécurité: Lecture publique, Écriture admin?
)

@category_router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin_user_entity)])
async def create_category_endpoint(category_data: CategoryCreate, service: ProductServiceDep):
    try:
        return await service.create_category(category_data)
    except (CategoryNotFoundException, InvalidOperationException) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur création catégorie: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne.")

@category_router.get("/", response_model=PaginatedCategoryResponse)
async def list_categories_endpoint(service: ProductServiceDep, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    try:
        return await service.list_categories(limit=limit, offset=offset)
    except Exception as e:
        logger.exception(f"Erreur listage catégories: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne.")

# TODO: Ajouter endpoints GET /categories/{id}, PUT /categories/{id} si nécessaire

@tags_router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin_user_entity)])
async def create_tag_endpoint(tag_data: TagCreate, service: ProductServiceDep):
    try:
        return await service.create_tag(tag_data)
    except InvalidOperationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur création tag: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne.")

@tags_router.get("/", response_model=PaginatedTagResponse)
async def list_tags_endpoint(service: ProductServiceDep, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    try:
        return await service.list_tags(limit=limit, offset=offset)
    except Exception as e:
        logger.exception(f"Erreur listage tags: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne.")

# TODO: Ajouter endpoints GET /tags/{id}, PUT /tags/{id} si nécessaire 