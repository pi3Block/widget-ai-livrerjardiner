"""
Implémentation des repositories pour les variants de produits.

Ce fichier contient les implémentations concrètes des repositories
utilisés dans le module product_variants.
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from src.product_variants.models import ProductVariant
from src.product_variants.interfaces.repositories import AbstractProductVariantRepository
from src.product_variants.exceptions import VariantNotFoundException, DuplicateSKUException

logger = logging.getLogger(__name__)


class SQLAlchemyProductVariantRepository(AbstractProductVariantRepository):
    """Implémentation SQLAlchemy du repository de variants de produits."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, variant_id: int) -> Optional[ProductVariant]:
        """Récupère une variante de produit par son ID."""
        stmt = (
            select(ProductVariant)
            .where(ProductVariant.id == variant_id)
            .options(selectinload(ProductVariant.product))
        )
        result = await self.session.execute(stmt)
        variant = result.scalar_one_or_none()
        
        if not variant:
            logger.debug(f"Variante ID {variant_id} non trouvée dans get_by_id().")
            return None
        
        return variant

    async def get_by_sku(self, sku: str) -> Optional[ProductVariant]:
        """Récupère une variante de produit par son SKU."""
        stmt = (
            select(ProductVariant)
            .where(ProductVariant.sku == sku)
            .options(selectinload(ProductVariant.product))
        )
        result = await self.session.execute(stmt)
        variant = result.scalar_one_or_none()
        
        if not variant:
            logger.debug(f"Variante SKU {sku} non trouvée dans get_by_sku().")
            return None
        
        return variant

    async def list_for_product(self, product_id: int, limit: int = 50, offset: int = 0) -> Tuple[List[ProductVariant], int]:
        """Liste les variantes pour un produit donné avec pagination et retourne le total."""
        # Requête pour les variantes
        stmt = (
            select(ProductVariant)
            .where(ProductVariant.product_id == product_id)
            .options(selectinload(ProductVariant.product))
            .order_by(ProductVariant.created_at.desc()) 
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        variants = result.scalars().all()

        # Requête pour le compte total
        count_stmt = (
            select(func.count(ProductVariant.id))
            .where(ProductVariant.product_id == product_id)
        )
        total_result = await self.session.execute(count_stmt)
        total_count = total_result.scalar_one() or 0

        return variants, total_count

    async def create(self, variant_data: Dict[str, Any]) -> ProductVariant:
        """Crée une nouvelle variante de produit."""
        new_variant = ProductVariant(**variant_data)
        
        self.session.add(new_variant)
        
        try:
            await self.session.flush() # Obtenir l'ID et vérifier contraintes
            logger.info(f"Variante ID {new_variant.id} créée pour produit {new_variant.product_id}.")
            return new_variant
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erreur intégrité création variante: {e}", exc_info=True)
            if "duplicate key value violates unique constraint" in str(e):
                raise DuplicateSKUException(sku=variant_data.get("sku", "unknown"))
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue création variante: {e}", exc_info=True)
            raise

    async def update(self, variant_id: int, variant_data: Dict[str, Any]) -> Optional[ProductVariant]:
        """Met à jour une variante de produit existante."""
        variant = await self.get_by_id(variant_id)
        if not variant:
            logger.warning(f"Tentative MAJ variante ID {variant_id} non trouvée.")
            return None
        
        # Mettre à jour les attributs
        for key, value in variant_data.items():
            if hasattr(variant, key):
                setattr(variant, key, value)
        
        try:
            await self.session.flush() # Appliquer le changement
            logger.info(f"Variante ID {variant_id} mise à jour.")
            return variant
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Erreur intégrité MAJ variante {variant_id}: {e}", exc_info=True)
            if "duplicate key value violates unique constraint" in str(e):
                raise DuplicateSKUException(sku=variant_data.get("sku", "unknown"))
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue MAJ variante {variant_id}: {e}", exc_info=True)
            raise

    async def delete(self, variant_id: int) -> bool:
        """Supprime une variante de produit."""
        variant = await self.get_by_id(variant_id)
        if not variant:
            logger.warning(f"Tentative suppression variante ID {variant_id} non trouvée.")
            return False
        
        try:
            await self.session.delete(variant)
            await self.session.flush() # Appliquer le changement
            logger.info(f"Variante ID {variant_id} supprimée.")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur inattendue suppression variante {variant_id}: {e}", exc_info=True)
            raise 