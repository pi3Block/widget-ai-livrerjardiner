# src/categories/repositories.py
import logging
from typing import List, Optional, Tuple

from fastcrud import FastCRUD
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.categories.exceptions import DuplicateCategoryNameException, CategoryNotFoundException # Import specific exceptions
from src.categories.interfaces.repositories import AbstractCategoryRepository
from src.categories.models import Category, CategoryCreate, CategoryRead, CategoryUpdate

logger = logging.getLogger(__name__)


class SQLAlchemyCategoryRepository(AbstractCategoryRepository):
    """Implémentation SQLAlchemy du repository des catégories avec FastCRUD."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.crud = FastCRUD[Category, CategoryCreate, CategoryUpdate, CategoryUpdate, CategoryRead, CategoryRead](Category)

    async def get_by_id(self, category_id: int) -> Optional[CategoryRead]:
        logger.debug(f"[CategoryRepository] Getting category by ID: {category_id}")
        category = await self.crud.get(db=self.db, id=category_id, schema_to_select=CategoryRead)
        if not category:
            logger.warning(f"[CategoryRepository] Category not found by ID: {category_id}")
        return category

    async def get_by_name(self, name: str) -> Optional[Category]:
        logger.debug(f"[CategoryRepository] Getting category by name: {name}")
        # Use schema_to_select=None to get the full table model
        category = await self.crud.get(db=self.db, schema_to_select=None, name=name)
        if not category:
            logger.warning(f"[CategoryRepository] Category not found by name: {name}")
        return category

    async def list(self, limit: int = 100, offset: int = 0) -> Tuple[List[CategoryRead], int]:
        logger.debug(f"[CategoryRepository] Listing categories: limit={limit}, offset={offset}")
        result = await self.crud.get_multi(
            db=self.db,
            limit=limit,
            offset=offset,
            schema_to_select=CategoryRead,
            sort_by="name"
        )
        return result.get('data', []), result.get('total', 0)

    async def create(self, category_data: CategoryCreate) -> CategoryRead:
        logger.debug(f"[CategoryRepository] Creating category: {category_data.name}")
        try:
            # FastCRUD create returns the ORM model instance
            created_category_orm = await self.crud.create(db=self.db, object=category_data)
            # Explicitly validate the ORM model into the Read schema
            # Ensure the session is flushed so all attributes (like ID) are loaded
            await self.db.flush()
            await self.db.refresh(created_category_orm)
            return CategoryRead.model_validate(created_category_orm)
        except IntegrityError as e: # Catch specific DB constraint errors
            await self.db.rollback() # Rollback on integrity error
            logger.warning(f"[CategoryRepository] Integrity error creating category {category_data.name}: {e}")
            # Check if it's a unique constraint violation for 'name'
            if "unique constraint" in str(e).lower() and "categories_name_key" in str(e).lower():
                 raise DuplicateCategoryNameException(category_data.name)
            raise # Re-raise other integrity errors
        except Exception as e:
            logger.error(f"[CategoryRepository] Unexpected error creating category {category_data.name}: {e}", exc_info=True)
            raise

    async def update(self, category_id: int, category_data: CategoryUpdate) -> Optional[CategoryRead]:
        logger.debug(f"[CategoryRepository] Updating category ID: {category_id}")
        try:
            # FastCRUD update returns the updated object or raises NotFoundError
            updated_category = await self.crud.update(
                db=self.db,
                id=category_id,
                object=category_data,
                schema_to_select=CategoryRead
            )
            return updated_category
        except IntegrityError as e:
            logger.warning(f"[CategoryRepository] Integrity error updating category {category_id}: {e}")
            if "unique constraint" in str(e).lower() and "categories_name_key" in str(e).lower():
                # Get the name from the update data if available for the exception
                updated_name = category_data.name if category_data.name else "<unknown>"
                raise DuplicateCategoryNameException(updated_name)
            raise
        except Exception as e:
             # Handle potential NotFoundError from FastCRUD if needed, though update might handle it
            # If FastCRUD's update doesn't raise NotFoundError but returns None/empty, you might need: 
            # current = await self.crud.get(db=self.db, id=category_id, schema_to_select=None)
            # if not current:
            #    raise CategoryNotFoundException(category_id)
            logger.error(f"[CategoryRepository] Error updating category {category_id}: {e}", exc_info=True)
            raise

    async def delete(self, category_id: int) -> Optional[Category]:
        logger.debug(f"[CategoryRepository] Deleting category ID: {category_id}")
        try:
            # FastCRUD delete returns the deleted object (full model) or raises NotFoundError
            deleted_category = await self.crud.delete(db=self.db, id=category_id)
            return deleted_category
        except Exception as e:
            # Handle potential NotFoundError from FastCRUD
            # If FastCRUD delete doesn't raise but returns None, you might check that:
            # if deleted_category is None:
            #    # Verify it didn't exist before raising not found
            #    existing = await self.crud.get(db=self.db, id=category_id)
            #    if not existing: raise CategoryNotFoundException(category_id)
            
            # Handle foreign key constraints if needed
            # if "foreign key constraint" in str(e).lower():
            #     logger.warning(f"Attempted to delete category {category_id} with existing dependencies.")
            #     raise ForeignKeyViolationError(f"Cannot delete category {category_id}, it's referenced by other entities.") # Define this exception

            logger.error(f"[CategoryRepository] Error deleting category {category_id}: {e}", exc_info=True)
            raise # Re-raise other exceptions 