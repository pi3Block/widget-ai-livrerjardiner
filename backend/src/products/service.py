import logging
from typing import Optional, List, TypeVar, Generic, Dict, Any
from sqlmodel import SQLModel
from sqlalchemy.exc import IntegrityError

# Import the Abstract Repository Interface
from .interfaces.repositories import AbstractProductRepository

# Import models and schemas for Product
from .models import (
    Product, ProductRead, ProductCreate, ProductUpdate, ProductReadWithDetails
)
# Import Category Schemas from categories module
from src.categories.models import CategoryRead, CategoryCreate, CategoryUpdate


# Import services from correct location
from src.product_variants.service import ProductVariantService
from src.categories.service import CategoryService

# Exceptions
from .exceptions import (
    ProductNotFoundException, CategoryNotFoundException,
    ProductUpdateFailedException, ProductCreationFailedException,
    InvalidOperationException
)
# Import exceptions from dependent services
from src.categories.exceptions import CategoryNotFoundException as CategoryServiceException

logger = logging.getLogger(__name__)

# --- Pagination Schemas ---
T = TypeVar('T', bound=SQLModel)

class PaginatedResponse(SQLModel, Generic[T]):
    items: List[T]
    total: int

class PaginatedProductResponse(PaginatedResponse[ProductReadWithDetails]): pass
class PaginatedCategoryResponse(PaginatedResponse[CategoryRead]): pass
# --- End Pagination Schemas ---

class ProductService:
    """Service managing product base information, delegating variant/category logic."""

    def __init__(
        self,
        product_repo: AbstractProductRepository, # Inject Repository
        category_service: CategoryService,
        variant_service: ProductVariantService
    ):
        self.product_repo = product_repo # Use the injected repository
        self.category_service = category_service
        self.variant_service = variant_service
        logger.info("ProductService initialized with repository and dependent services.")

    # --- Product Methods (using Repository) ---
    async def get_product(self, product_id: int) -> Optional[ProductReadWithDetails]:
        """Retrieves a detailed product by ID using the repository and variant service."""
        logger.debug(f"[ProductService] Get Product ID: {product_id}")
        product_entity = await self.product_repo.get_by_id_with_relations(id=product_id, relations=["category"])
        if not product_entity:
            raise ProductNotFoundException(product_id)
        product_base_read = ProductRead.model_validate(product_entity)
        try:
            variants_paginated = await self.variant_service.list_variants_for_product(product_id, limit=1000, offset=0)
            variants_details = variants_paginated.items if variants_paginated else []
        except Exception as e:
            logger.error(f"[ProductService] Error fetching variants for product {product_id}: {e}", exc_info=True)
            variants_details = []
        product_details = ProductReadWithDetails(
            **product_base_read.model_dump(exclude={"variants"}),
            variants=variants_details
        )
        return product_details

    async def list_products(
        self, limit: int, offset: int,
        category_id: Optional[int] = None,
        search_term: Optional[str] = None,
    ) -> PaginatedProductResponse:
        """Lists products using the repository with filters and pagination."""
        filters: Dict[str, Any] = {}
        if category_id is not None: filters['category_id'] = category_id
        if search_term: filters['name__icontains'] = search_term
        logger.debug(f"[ProductService] List Products: limit={limit}, offset={offset}, filters={filters}")
        product_entities, total_count = await self.product_repo.list(
            limit=limit, offset=offset, filters=filters, include_relations=["category"], sort_by="name"
        )
        product_responses: List[ProductReadWithDetails] = []
        for p_entity in product_entities:
            p_base_read = ProductRead.model_validate(p_entity)
            try:
                variants_paginated = await self.variant_service.list_variants_for_product(p_entity.id, limit=1000, offset=0)
                variants_details = variants_paginated.items if variants_paginated else []
            except Exception as e:
                 logger.error(f"[ProductService] Error fetching variants for product {p_entity.id} during list: {e}", exc_info=True)
                 variants_details = []
            p_details = ProductReadWithDetails(
                **p_base_read.model_dump(exclude={"variants"}),
                variants=variants_details
            )
            product_responses.append(p_details)
        return PaginatedProductResponse(items=product_responses, total=total_count)

    async def create_product(self, product_data: ProductCreate) -> ProductReadWithDetails:
        """Creates a new product using the repository, validating category first."""
        logger.info(f"[ProductService] Create Product: {product_data.name}")
        if product_data.category_id:
            try:
                await self.category_service.get_category(product_data.category_id)
            except CategoryServiceException as e:
                 raise CategoryNotFoundException(product_data.category_id) from e
        try:
            created_product_entity = await self.product_repo.create(data=product_data)
            logger.info(f"[ProductService] Product ID {created_product_entity.id} created via repo.")
            full_product = await self.get_product(created_product_entity.id)
            if not full_product:
                 logger.error(f"[ProductService] Failed critical: Could not reload product ID {created_product_entity.id} after creation.")
                 raise ProductCreationFailedException("Error reloading product immediately after creation.")
            return full_product
        except ProductCreationFailedException as e:
             logger.error(f"[ProductService] Repo failed creating product {product_data.name}: {e}", exc_info=True)
             raise
        except Exception as e:
            logger.error(f"[ProductService] Unexpected error creating product {product_data.name}: {e}", exc_info=True)
            raise ProductCreationFailedException(f"Internal error during product creation process: {e}")

    async def update_product(self, product_id: int, product_data: ProductUpdate) -> ProductReadWithDetails:
        """Updates a product's base info using the repository, validates category."""
        logger.info(f"[ProductService] Update Product ID: {product_id}")
        if product_data.category_id is not None:
             try:
                 await self.category_service.get_category(product_data.category_id)
             except CategoryServiceException as e:
                 raise CategoryNotFoundException(product_data.category_id) from e
        try:
            updated_product_entity = await self.product_repo.update(id=product_id, data=product_data)
            if not updated_product_entity:
                 logger.warning(f"[ProductService] Repo update for {product_id} returned None. Fetching current state.")
                 current_product = await self.get_product(product_id)
                 if not current_product:
                    raise ProductNotFoundException(product_id)
                 return current_product
            logger.info(f"[ProductService] Product ID {product_id} updated via repo.")
            full_product = await self.get_product(updated_product_entity.id)
            if not full_product:
                 logger.error(f"[ProductService] Failed critical: Could not reload product ID {updated_product_entity.id} after update.")
                 raise ProductUpdateFailedException("Error reloading product immediately after update.")
            return full_product
        except ProductNotFoundException:
             logger.warning(f"[ProductService] Product not found during update process for ID: {product_id}")
             raise
        except ProductUpdateFailedException as e:
             logger.error(f"[ProductService] Repo failed updating product {product_id}: {e}", exc_info=True)
             raise
        except Exception as e:
            logger.error(f"[ProductService] Unexpected error updating product {product_id}: {e}", exc_info=True)
            raise ProductUpdateFailedException(f"Internal error during product update process: {e}")

    async def delete_product(self, product_id: int) -> bool:
        """Deletes a product using the repository. Assumes DB cascade handles variants."""
        logger.info(f"[ProductService] Delete Product ID: {product_id}")
        try:
            deleted_product = await self.product_repo.delete(id=product_id)
            if deleted_product:
                logger.info(f"[ProductService] Product ID {product_id} deleted via repo.")
                return True
            else:
                logger.error(f"[ProductService] Repo delete for {product_id} returned None unexpectedly.")
                exists = await self.product_repo.get_by_id(product_id)
                if exists:
                    raise InvalidOperationException(f"Deletion failed for product {product_id} for unknown reasons.")
                else:
                    logger.warning(f"[ProductService] Product {product_id} not found after delete returned None. Assuming deleted.")
                    return True
        except ProductNotFoundException:
             logger.warning(f"[ProductService] Product not found for deletion: ID {product_id}")
             raise
        except InvalidOperationException as e:
            logger.error(f"[ProductService] Deletion constraint violation for product {product_id}: {e}", exc_info=True)
            raise InvalidOperationException(f"Cannot delete product {product_id}, likely due to dependencies: {e}") from e
        except Exception as e:
            logger.error(f"[ProductService] Unexpected error deleting product {product_id}: {e}", exc_info=True)
            raise InvalidOperationException(f"Could not delete product {product_id}: {e}")

    # --- Category Methods (Delegated to CategoryService) ---
    async def get_category(self, category_id: int) -> Optional[CategoryRead]:
        """Retrieves a category via CategoryService."""
        logger.debug(f"[ProductService] Delegating Get Category ID: {category_id} to CategoryService")
        try:
            return await self.category_service.get_category(category_id)
        except CategoryServiceException as e:
             raise CategoryNotFoundException(category_id) from e

    async def list_categories(self, limit: int = 100, offset: int = 0) -> PaginatedCategoryResponse:
        """Lists categories via CategoryService."""
        logger.debug(f"[ProductService] Delegating List Categories to CategoryService")
        return await self.category_service.list_categories(limit=limit, offset=offset)

    async def create_category(self, category_data: CategoryCreate) -> CategoryRead:
        """Creates a category via CategoryService."""
        logger.debug(f"[ProductService] Delegating Create Category to CategoryService")
        try:
            return await self.category_service.create_category(category_data)
        except Exception as e:
            logger.error(f"[ProductService] Error during category creation delegation: {e}", exc_info=True)
            raise InvalidOperationException(f"Failed to create category: {e}")

    async def update_category(self, category_id: int, category_data: CategoryUpdate) -> Optional[CategoryRead]:
        """Updates a category via CategoryService."""
        logger.debug(f"[ProductService] Delegating Update Category ID: {category_id} to CategoryService")
        try:
            return await self.category_service.update_category(category_id, category_data)
        except CategoryServiceException as e:
             raise CategoryNotFoundException(category_id) from e
        except Exception as e:
             logger.error(f"[ProductService] Error during category update delegation for {category_id}: {e}", exc_info=True)
             raise InvalidOperationException(f"Failed to update category {category_id}: {e}")

    async def delete_category(self, category_id: int) -> bool:
        """Deletes a category via CategoryService."""
        logger.debug(f"[ProductService] Delegating Delete Category ID: {category_id} to CategoryService")
        try:
             await self.category_service.delete_category(category_id)
             return True
        except CategoryServiceException as e:
             logger.warning(f"CategoryService reported issue deleting category {category_id}: {e}")
             if isinstance(e, CategoryNotFoundException):
                 raise
             raise InvalidOperationException(f"Could not delete category {category_id}: {e}") from e
        except IntegrityError as e: # Catch potential DB constraint errors
             logger.error(f"[ProductService] Integrity error during category deletion delegation for {category_id}: {e}", exc_info=True)
             raise InvalidOperationException(f"Cannot delete category {category_id}, it is likely referenced by products.")
        except Exception as e:
             logger.error(f"Error during category deletion delegation for {category_id}: {e}", exc_info=True)
             raise InvalidOperationException(f"Could not delete category {category_id}")
        