"""
Interfaces pour les repositories de variants de produits.

Ce fichier contient les interfaces (classes abstraites) pour les repositories
utilisés dans le module product_variants.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple

from src.product_variants.models import ProductVariant


class AbstractProductVariantRepository(ABC):
    """Interface pour le repository des variantes de produits."""
    
    @abstractmethod
    async def get_by_id(self, variant_id: int) -> Optional[ProductVariant]:
        """Récupère une variante de produit par son ID."""
        pass
    
    @abstractmethod
    async def get_by_sku(self, sku: str) -> Optional[ProductVariant]:
        """Récupère une variante de produit par son SKU."""
        pass
    
    @abstractmethod
    async def list_for_product(self, product_id: int, limit: int = 50, offset: int = 0) -> Tuple[List[ProductVariant], int]:
        """Liste les variantes pour un produit donné avec pagination et retourne le total."""
        pass
    
    @abstractmethod
    async def create(self, variant_data: Dict[str, Any]) -> ProductVariant:
        """Crée une nouvelle variante de produit."""
        pass
    
    @abstractmethod
    async def update(self, variant_id: int, variant_data: Dict[str, Any]) -> Optional[ProductVariant]:
        """Met à jour une variante de produit existante."""
        pass
    
    @abstractmethod
    async def delete(self, variant_id: int) -> bool:
        """Supprime une variante de produit."""
        pass 