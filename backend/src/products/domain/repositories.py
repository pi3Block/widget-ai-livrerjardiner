from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple

from .entities import Category, Tag, Product, ProductVariant, Stock
from .exceptions import ProductNotFoundException, CategoryNotFoundException, VariantNotFoundException, DuplicateSKUException

# Interfaces Abstraites pour les Repositories
# Elles définissent le contrat que les implémentations concrètes (ex: SQLAlchemy) devront respecter.

class AbstractCategoryRepository(ABC):
    """Interface pour le repository des Catégories."""
    @abstractmethod
    async def get_by_id(self, category_id: int) -> Optional[Category]:
        raise NotImplementedError

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Category]:
        raise NotImplementedError

    @abstractmethod
    async def add(self, category_data: Dict[str, Any]) -> Category:
        raise NotImplementedError
    
    @abstractmethod
    async def update(self, category_id: int, update_data: Dict[str, Any]) -> Optional[Category]:
        raise NotImplementedError
    
    # delete ? (Attention aux produits liés)

class AbstractTagRepository(ABC):
    """Interface pour le repository des Tags."""
    @abstractmethod
    async def get_by_id(self, tag_id: int) -> Optional[Tag]:
        raise NotImplementedError

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Tag]:
        raise NotImplementedError

    @abstractmethod
    async def add(self, tag_data: Dict[str, Any]) -> Tag:
        raise NotImplementedError

    # update, delete ?

class AbstractProductRepository(ABC):
    """Interface pour le repository des Produits (entité principale)."""
    @abstractmethod
    async def get_by_id(self, product_id: int, include_relations: List[str] = []) -> Optional[Product]:
        """Récupère un produit par ID, avec option de charger relations (variants, category, tags)."""
        raise NotImplementedError

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0, filter_params: Optional[Dict[str, Any]] = None, include_relations: List[str] = []) -> Tuple[List[Product], int]:
        """Liste les produits avec filtres, pagination et chargement de relations. Retourne aussi le compte total."""
        raise NotImplementedError

    @abstractmethod
    async def add(self, product_data: Dict[str, Any], tag_ids: Optional[List[int]] = None) -> Product:
        """Ajoute un produit, potentiellement avec des tags."""
        raise NotImplementedError

    @abstractmethod
    async def update(self, product_id: int, update_data: Dict[str, Any], tag_ids: Optional[List[int]] = None) -> Optional[Product]:
        """Met à jour un produit, potentiellement avec des tags."""
        raise NotImplementedError

    # delete ? (Attention aux variantes/commandes liées)

class AbstractProductVariantRepository(ABC):
    """Interface pour le repository des Variantes de Produit."""
    @abstractmethod
    async def get_by_id(self, variant_id: int) -> Optional[ProductVariant]:
        raise NotImplementedError
    
    @abstractmethod
    async def get_by_sku(self, sku: str) -> Optional[ProductVariant]:
        raise NotImplementedError

    @abstractmethod
    async def list_for_product(self, product_id: int, limit: int = 50, offset: int = 0) -> List[ProductVariant]:
        raise NotImplementedError

    @abstractmethod
    async def add(self, variant_data: Dict[str, Any]) -> ProductVariant:
        """Ajoute une variante. La création de l'entrée stock associée est gérée par le service."""
        raise NotImplementedError

    @abstractmethod
    async def update(self, variant_id: int, update_data: Dict[str, Any]) -> Optional[ProductVariant]:
        raise NotImplementedError

    # delete ? (Attention stock/commandes/devis liés)

class AbstractStockRepository(ABC):
    """Interface pour le repository des Stocks (par variante)."""
    @abstractmethod
    async def get_for_variant(self, variant_id: int) -> Optional[Stock]:
        """Récupère l'info stock pour une variante."""
        raise NotImplementedError

    @abstractmethod
    async def add_or_update(self, stock_data: Dict[str, Any]) -> Stock:
        """Crée ou met à jour l'entrée stock pour une variante."""
        raise NotImplementedError

    @abstractmethod
    async def update_quantity(self, variant_id: int, quantity_change: int) -> Optional[Stock]:
        """Met à jour la quantité de manière atomique (incrémente/décrémente). Retourne le nouvel état si succès."""
        raise NotImplementedError

    @abstractmethod
    async def list_low_stock(self, threshold: int, limit: int = 100) -> List[Stock]:
        """Liste les stocks en dessous d'un certain seuil."""
        raise NotImplementedError

    # delete ? Généralement pas utile, on met le stock à 0. 