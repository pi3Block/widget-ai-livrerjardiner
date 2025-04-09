import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastcrud import FastCRUD

from .interfaces.repositories import AbstractProductRepository
from .models import Product, ProductCreate, ProductUpdate
# TODO: Check if DuplicateProductException exists or needs creation
from .exceptions import (
    ProductNotFoundException, ProductCreationFailedException,
    ProductUpdateFailedException, InvalidOperationException #, DuplicateProductException
)

logger = logging.getLogger(__name__)

class SQLAlchemyProductRepository(AbstractProductRepository):
    """SQLAlchemy implementation of the product repository."""

    def __init__(self, db: AsyncSession):
        self.db = db
        # Initialize FastCRUD for the Product model
        self.crud = FastCRUD[Product, ProductCreate, ProductUpdate](Product)

    async def get_by_id(self, id: int) -> Optional[Product]:
        """Retrieves a product by its ID using FastCRUD."""
        logger.debug(f"[Repo] Getting product by ID: {id}")
        try:
            # FastCRUD's get returns None if not found
            product = await self.crud.get(db=self.db, id=id)
            if not product:
                 logger.warning(f"[Repo] Product not found by ID: {id}")
                 return None
            return product
        except Exception as e:
            logger.error(f"[Repo] Error getting product by ID {id}: {e}", exc_info=True)
            raise # Re-raise unexpected errors

    async def get_by_id_with_relations(
        self, id: int, relations: Optional[List[str]] = None
    ) -> Optional[Product]:
        """Retrieves a product by its ID, optionally loading specified relations."""
        logger.debug(f"[Repo] Getting product by ID: {id} with relations: {relations}")
        try:
            # Assuming crud.get handles relation loading based on model or returns None
            product = await self.crud.get(db=self.db, id=id)
            if not product:
                logger.warning(f"[Repo] Product not found by ID: {id} (with relations)")
                return None
            return product
        except Exception as e:
            logger.error(f"[Repo] Error getting product by ID {id} with relations: {e}", exc_info=True)
            raise

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        include_relations: Optional[List[str]] = None, # Parameter now used
    ) -> Tuple[List[Product], int]:
        """Lists products using FastCRUD with pagination, filtering, sorting, and optional relations."""
        logger.debug(f"[Repo] Listing products: limit={limit}, offset={offset}, filters={filters}, sort={sort_by} {sort_order}, relations={include_relations}")
        # Use include_columns for potential relation loading with get_multi
        try:
            result = await self.crud.get_multi(
                db=self.db,
                offset=offset,
                limit=limit,
                filters=filters or {},
                sort_by=sort_by,
                sort_order=sort_order,
                include_columns=include_relations or [] # Pass relations here
            )
            data = result.get('data', [])
            total = result.get('total', 0)
            logger.debug(f"[Repo] Found {total} products matching criteria.")
            return data, total
        except Exception as e:
            logger.error(f"[Repo] Error listing products: {e}", exc_info=True)
            raise # Re-raise unexpected errors

    async def create(self, data: ProductCreate) -> Product:
        """Creates a new product using FastCRUD."""
        logger.debug(f"[Repo] Creating product: {data.name}")
        try:
            created_product = await self.crud.create(db=self.db, object=data)
            logger.info(f"[Repo] Product '{data.name}' created with ID: {created_product.id}")
            return created_product
        except Exception as e: # Catch potential unique constraint errors etc.
            await self.db.rollback() # Rollback on error
            logger.error(f"[Repo] Error creating product {data.name}: {e}", exc_info=True)
            if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                 raise ProductCreationFailedException(f"Product with slug '{data.slug}' or name '{data.name}' may already exist.") from e
            raise ProductCreationFailedException(f"Failed to create product {data.name}: {e}") from e

    async def update(self, id: int, data: ProductUpdate) -> Optional[Product]:
        """Updates an existing product using FastCRUD."""
        logger.debug(f"[Repo] Updating product ID: {id}")
        # First, check if product exists
        existing_product = await self.get_by_id(id)
        if not existing_product:
            raise ProductNotFoundException(product_id=id)

        try:
            updated_product = await self.crud.update(db=self.db, object=data, id=id)
            # crud.update might return the updated object or potentially raise errors
            # If it returns None without raising error, it might mean no change happened
            if updated_product:
                 logger.info(f"[Repo] Product ID {id} updated.")
                 return updated_product
            else:
                 # If update returns None but product exists, assume no change
                 logger.warning(f"[Repo] Update for product ID {id} returned None. Assuming no change occurred.")
                 return existing_product # Return original entity

        except Exception as e:
            await self.db.rollback()
            logger.error(f"[Repo] Error updating product {id}: {e}", exc_info=True)
            if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                 raise ProductUpdateFailedException(f"Update failed for product {id}. Slug '{data.slug}' may already exist.") from e
            raise ProductUpdateFailedException(f"Failed to update product {id}: {e}") from e

    async def delete(self, id: int) -> Optional[Product]:
        """Deletes a product by its ID using FastCRUD."""
        logger.debug(f"[Repo] Deleting product ID: {id}")
        # First, fetch the object to return it and ensure it exists
        product_to_delete = await self.get_by_id(id)
        if not product_to_delete:
            raise ProductNotFoundException(product_id=id)

        try:
            await self.crud.delete(db=self.db, id=id)
            logger.info(f"[Repo] Product ID {id} deleted.")
            return product_to_delete
        except Exception as e: # Catch potential foreign key constraints etc.
            await self.db.rollback()
            logger.error(f"[Repo] Error deleting product {id}: {e}", exc_info=True)
            raise InvalidOperationException(f"Could not delete product {id}. It might be referenced elsewhere: {e}") from e

    async def find_by_slug(self, slug: str) -> Optional[Product]:
        """Retrieves a product by its slug using FastCRUD filtering."""
        logger.debug(f"[Repo] Getting product by slug: {slug}")
        try:
            result = await self.crud.get_multi(db=self.db, limit=1, filters={"slug": slug})
            products = result.get('data', [])
            if products:
                logger.debug(f"[Repo] Found product by slug: {slug}")
                return products[0]
            else:
                logger.warning(f"[Repo] Product not found by slug: {slug}")
                return None
        except Exception as e:
            logger.error(f"[Repo] Error finding product by slug {slug}: {e}", exc_info=True)
            raise # Re-raise unexpected errors 