from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple

# Import the necessary models and schemas
from src.products.models import Product, ProductCreate, ProductUpdate

class AbstractProductRepository(ABC):
    """Abstract interface for product data access operations."""

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[Product]:
        """Retrieves a product by its ID."""
        pass

    @abstractmethod
    async def get_by_id_with_relations(
        self, id: int, relations: Optional[List[str]] = None
    ) -> Optional[Product]:
        """Retrieves a product by its ID, optionally loading specified relations."""
        pass

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        include_relations: Optional[List[str]] = None,
    ) -> Tuple[List[Product], int]:
        """Lists products with pagination, filtering, sorting, and optional relation loading."""
        pass

    @abstractmethod
    async def create(self, data: ProductCreate) -> Product:
        """Creates a new product."""
        pass

    @abstractmethod
    async def update(self, id: int, data: ProductUpdate) -> Optional[Product]:
        """Updates an existing product."""
        pass

    @abstractmethod
    async def delete(self, id: int) -> Optional[Product]:
        """Deletes a product by its ID. Returns the deleted product or None if not found."""
        pass

    @abstractmethod
    async def find_by_slug(self, slug: str) -> Optional[Product]:
        """Retrieves a product by its slug."""
        pass 