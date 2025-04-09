import logging
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
# Remove FastCRUD import if no longer needed directly here
# from fastcrud import FastCRUD

# Database session dependency
from src.database import get_db_session

# Import the necessary repository interface and implementation
from .interfaces.repositories import AbstractProductRepository
from .repositories import SQLAlchemyProductRepository

# Import necessary models (only those directly used or returned by repo/service)
# Assuming Product model is needed for type hints if not already covered by schemas
# from .models import Product # Check if needed

# Import dependent services and their dependencies
from src.categories.dependencies import CategoryServiceDep
from src.product_variants.dependencies import VariantServiceDep

# Import the ProductService
from .service import ProductService

logger = logging.getLogger(__name__)

# --- Dependency Getters --- #

# Dependency for DB Session
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]

# Dependency Provider for Product Repository
def get_product_repository(
    session: SessionDep # Inject the DB session
) -> AbstractProductRepository: # Return the interface type
    """Provides an instance of the SQLAlchemyProductRepository."""
    logger.debug("Providing SQLAlchemyProductRepository")
    return SQLAlchemyProductRepository(db=session)

# Type hint for injecting the Product Repository
ProductRepositoryDep = Annotated[AbstractProductRepository, Depends(get_product_repository)]


# --- Dependency Getter for the Product Service --- #

def get_product_service(
    # Inject the repository implementation via the dependency provider
    product_repo: ProductRepositoryDep,
    # Inject dependent services
    category_service: CategoryServiceDep, # Keep this dependency
    variant_service: VariantServiceDep,   # Keep this dependency
    # Remove direct DB session injection as service delegates DB ops to repo
    # db: SessionDep
) -> ProductService:
    """Provides an instance of the ProductService with its dependencies."""
    logger.debug("Providing ProductService with repository and dependent services")
    # Ensure the arguments match the ProductService.__init__ signature
    return ProductService(
        product_repo=product_repo,
        category_service=category_service,
        variant_service=variant_service
    )

# Type hint for injecting the ProductService into endpoints
ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]

