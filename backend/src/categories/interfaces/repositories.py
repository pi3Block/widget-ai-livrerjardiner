# src/categories/interfaces/repositories.py
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from src.categories.models import Category, CategoryCreate, CategoryRead, CategoryUpdate


class AbstractCategoryRepository(ABC):
    """Interface abstraite pour le repository des catégories."""

    @abstractmethod
    async def get_by_id(self, category_id: int) -> Optional[CategoryRead]:
        """Récupère une catégorie par son ID (schéma Read)."""
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Category]:
        """Récupère une catégorie par son nom (modèle Table)."""
        pass

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> Tuple[List[CategoryRead], int]:
        """Liste les catégories avec pagination (schéma Read)."""
        pass

    @abstractmethod
    async def create(self, category_data: CategoryCreate) -> CategoryRead:
        """Crée une nouvelle catégorie (retourne schéma Read)."""
        pass

    @abstractmethod
    async def update(self, category_id: int, category_data: CategoryUpdate) -> Optional[CategoryRead]:
        """Met à jour une catégorie (retourne schéma Read)."""
        pass

    @abstractmethod
    async def delete(self, category_id: int) -> Optional[Category]:
        """Supprime une catégorie (retourne le modèle supprimé ou None)."""
        pass 