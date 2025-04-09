import logging
from typing import List, Optional, TypeVar, Generic
from sqlmodel import SQLModel

# Importer l'interface du repository
from .interfaces.repositories import AbstractCategoryRepository
from .models import Category, CategoryCreate, CategoryUpdate, CategoryRead
# Importer les exceptions spécifiques
from .exceptions import (
    CategoryNotFoundException,
    DuplicateCategoryNameException,
    CategoryUpdateFailedException,
    CategoryCreationFailedException,
    InvalidCategoryOperationException
)

logger = logging.getLogger(__name__)

# --- Pagination Schema (Optionnel, mais bon pour la cohérence) ---
T = TypeVar('T', bound=SQLModel)
class PaginatedResponse(SQLModel, Generic[T]):
    items: List[T]
    total: int
class PaginatedCategoryResponse(PaginatedResponse[CategoryRead]): pass
# --------------------------------------------------------------------

class CategoryService:
    """Service applicatif pour la gestion des catégories via Repository."""

    def __init__(self, repository: AbstractCategoryRepository):
        self.repository = repository
        logger.info("CategoryService initialized with repository.")

    async def list_categories(self, limit: int = 100, offset: int = 0) -> PaginatedCategoryResponse:
        """Liste les catégories avec pagination via le repository."""
        logger.debug(f"[CategoryService] List Categories: limit={limit}, offset={offset}")
        try:
            categories, total_count = await self.repository.list(limit=limit, offset=offset)
            return PaginatedCategoryResponse(items=categories, total=total_count)
        except Exception as e:
            logger.error(f"[CategoryService] Error listing categories via repository: {e}", exc_info=True)
            raise InvalidCategoryOperationException(f"Erreur interne lors de la récupération des catégories: {e}")

    async def get_category(self, category_id: int) -> CategoryRead:
        """Récupère une catégorie par ID via le repository."""
        logger.debug(f"[CategoryService] Get Category ID: {category_id}")
        category = await self.repository.get_by_id(category_id=category_id)
        if not category:
            raise CategoryNotFoundException(category_id)
        return category

    async def create_category(self, category_data: CategoryCreate) -> CategoryRead:
        """Crée une nouvelle catégorie via le repository."""
        logger.info(f"[CategoryService] Create Category: {category_data.name}")
        existing_category = await self.repository.get_by_name(name=category_data.name)
        if existing_category:
            raise DuplicateCategoryNameException(category_data.name)

        try:
            created_category = await self.repository.create(category_data=category_data)
            logger.info(f"[CategoryService] Category ID {created_category.id} created via repository.")
            return created_category
        except DuplicateCategoryNameException:
            raise
        except Exception as e:
            logger.error(f"[CategoryService] Error creating category {category_data.name} via repository: {e}", exc_info=True)
            raise CategoryCreationFailedException(f"Erreur interne lors de la création de la catégorie: {e}")

    async def update_category(self, category_id: int, category_data: CategoryUpdate) -> CategoryRead:
        """Met à jour une catégorie existante via le repository."""
        logger.info(f"[CategoryService] Update Category ID: {category_id}")
        if category_data.name:
            existing_category_with_name = await self.repository.get_by_name(name=category_data.name)
            if existing_category_with_name and existing_category_with_name.id != category_id:
                raise DuplicateCategoryNameException(category_data.name)

        try:
            updated_category = await self.repository.update(category_id=category_id, category_data=category_data)
            if updated_category is None:
                existing = await self.repository.get_by_id(category_id=category_id)
                if not existing:
                    raise CategoryNotFoundException(category_id)
                raise CategoryUpdateFailedException(category_id, message="La mise à jour n'a pas retourné de catégorie mise à jour.")

            logger.info(f"[CategoryService] Category ID {category_id} updated via repository.")
            return updated_category
        except DuplicateCategoryNameException:
            raise
        except CategoryNotFoundException:
            raise
        except Exception as e:
            logger.error(f"[CategoryService] Error updating category {category_id} via repository: {e}", exc_info=True)
            raise CategoryUpdateFailedException(category_id, message=f"Erreur interne lors de la mise à jour: {e}")

    async def delete_category(self, category_id: int) -> None:
        """Supprime une catégorie via le repository."""
        logger.info(f"[CategoryService] Delete Category ID: {category_id}")
        try:
            deleted_category = await self.repository.delete(category_id=category_id)
            if deleted_category is None:
                existing = await self.repository.get_by_id(category_id=category_id)
                if not existing:
                    raise CategoryNotFoundException(category_id)
                raise InvalidCategoryOperationException(f"La suppression de la catégorie {category_id} a échoué sans erreur explicite.")

            logger.info(f"[CategoryService] Category ID {category_id} deleted via repository.")
        except CategoryNotFoundException:
            raise
        except Exception as e:
            logger.error(f"[CategoryService] Error deleting category {category_id} via repository: {e}", exc_info=True)
            raise InvalidCategoryOperationException(f"Erreur interne lors de la suppression de la catégorie {category_id}: {e}") 