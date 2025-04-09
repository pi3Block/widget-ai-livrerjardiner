"""
Module product_variants.

Ce module gère les variantes de produits dans l'application.
Il fournit les fonctionnalités nécessaires pour :
- Gérer les variantes de produits (création, modification, suppression)
- Gérer les stocks des variantes
- Gérer les prix des variantes
- Gérer les attributs des variantes
"""

from .models import ProductVariant
from .schemas import (
    ProductVariantCreate,
    ProductVariantUpdate,
    ProductVariantResponse,
    ProductVariantList
)
from .repositories import (
    AbstractProductVariantRepository,
    SQLAlchemyProductVariantRepository
)
from .exceptions import (
    ProductVariantException,
    VariantNotFoundException,
    DuplicateSKUException,
    InvalidVariantDataException,
    VariantUpdateException,
    VariantDeleteException
)

__all__ = [
    'ProductVariant',
    'ProductVariantCreate',
    'ProductVariantUpdate',
    'ProductVariantResponse',
    'ProductVariantList',
    'AbstractProductVariantRepository',
    'SQLAlchemyProductVariantRepository',
    'ProductVariantException',
    'VariantNotFoundException',
    'DuplicateSKUException',
    'InvalidVariantDataException',
    'VariantUpdateException',
    'VariantDeleteException'
] 