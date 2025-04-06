import logging
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Correction de l'import pour get_db_session
from ...core.database import get_db_session

# Interfaces des Repositories (contrats)
from src.products.domain.repositories import (
    AbstractCategoryRepository, AbstractTagRepository, AbstractProductRepository, 
    AbstractProductVariantRepository, AbstractStockRepository
)
# Implémentations concrètes des Repositories (SQLAlchemy)
from src.products.infrastructure.persistence import (
    SQLAlchemyCategoryRepository, SQLAlchemyTagRepository, SQLAlchemyProductRepository,
    SQLAlchemyProductVariantRepository, SQLAlchemyStockRepository
)
# Services Applicatifs - Correction de l'import pour chemin relatif
from ..application.services import ProductService

logger = logging.getLogger(__name__)

# --- Fonctions de Dépendance pour les Repositories ---
# Ces fonctions créent une instance du repository concret avec la session DB

def get_category_repository(db: AsyncSession = Depends(get_db_session)) -> AbstractCategoryRepository:
    """Injecte une instance de SQLAlchemyCategoryRepository."""
    logger.debug("Fourniture de SQLAlchemyCategoryRepository")
    return SQLAlchemyCategoryRepository(session=db)

def get_tag_repository(db: AsyncSession = Depends(get_db_session)) -> AbstractTagRepository:
    """Injecte une instance de SQLAlchemyTagRepository."""
    logger.debug("Fourniture de SQLAlchemyTagRepository")
    return SQLAlchemyTagRepository(session=db)

def get_product_repository(
    tag_repo: Annotated[AbstractTagRepository, Depends(get_tag_repository)],
    db: AsyncSession = Depends(get_db_session)
) -> AbstractProductRepository:
    """Injecte une instance de SQLAlchemyProductRepository."""
    logger.debug("Fourniture de SQLAlchemyProductRepository")
    return SQLAlchemyProductRepository(session=db, tag_repo=tag_repo)

def get_variant_repository(db: AsyncSession = Depends(get_db_session)) -> AbstractProductVariantRepository:
    """Injecte une instance de SQLAlchemyProductVariantRepository."""
    logger.debug("Fourniture de SQLAlchemyProductVariantRepository")
    return SQLAlchemyProductVariantRepository(session=db)

def get_stock_repository(db: AsyncSession = Depends(get_db_session)) -> AbstractStockRepository:
    """Injecte une instance de SQLAlchemyStockRepository."""
    logger.debug("Fourniture de SQLAlchemyStockRepository")
    return SQLAlchemyStockRepository(session=db)

# --- Fonctions de Dépendance pour les Services ---
# Ces fonctions créent une instance du service en injectant ses dépendances (repositories)

# Utilisation de Annotated pour une meilleure lisibilité (optionnel mais recommandé)
CategoryRepositoryDep = Annotated[AbstractCategoryRepository, Depends(get_category_repository)]
TagRepositoryDep = Annotated[AbstractTagRepository, Depends(get_tag_repository)]
ProductRepositoryDep = Annotated[AbstractProductRepository, Depends(get_product_repository)]
VariantRepositoryDep = Annotated[AbstractProductVariantRepository, Depends(get_variant_repository)]
StockRepositoryDep = Annotated[AbstractStockRepository, Depends(get_stock_repository)]

def get_product_service(
    product_repo: ProductRepositoryDep,
    category_repo: CategoryRepositoryDep,
    tag_repo: TagRepositoryDep,
    variant_repo: VariantRepositoryDep,
    stock_repo: StockRepositoryDep
) -> ProductService:
    """Injecte une instance de ProductService avec toutes ses dépendances."""
    logger.debug("Fourniture de ProductService")
    return ProductService(
        product_repo=product_repo,
        category_repo=category_repo,
        tag_repo=tag_repo,
        variant_repo=variant_repo,
        stock_repo=stock_repo
    )

# Type hints pour l'injection directe dans les endpoints
ProductServiceDep = Annotated[ProductService, Depends(get_product_service)] 