"""
Interfaces pour le module LLM.

Ce fichier contient les interfaces (classes abstraites) pour les repositories
et services utilisés dans le module LLM.
"""
from abc import ABC, abstractmethod
from typing import Optional

from src.product_variants.models import ProductVariant
from src.stock.models import Stock


class AbstractProductVariantRepository(ABC):
    """Interface pour le repository des variantes de produits."""
    
    @abstractmethod
    async def get_by_sku(self, sku: str) -> Optional[ProductVariant]:
        """Récupère une variante de produit par son SKU."""
        pass


class AbstractStockRepository(ABC):
    """Interface pour le repository de stock."""
    
    @abstractmethod
    async def get_for_variant(self, variant_id: int) -> Optional[Stock]:
        """Récupère le stock pour une variante donnée."""
        pass


class AbstractAddressRepository(ABC):
    """Interface pour le repository des adresses."""
    
    @abstractmethod
    async def get_default_address(self, user_id: int):
        """Récupère l'adresse par défaut d'un utilisateur."""
        pass 