import logging
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
# Remove FastCRUD import if no longer needed elsewhere in this file
# from fastcrud import FastCRUD

# Database session
from src.database import get_db_session

# Models
# from src.quotes.models import Quote, QuoteItem # No longer needed for CRUD dependencies

# Service
from src.quotes.service import QuoteService

# Repository Interface and Implementation
from src.quotes.interfaces.repositories import AbstractQuoteRepository
from src.quotes.repositories import SQLAlchemyQuoteRepository

# Import des dépendances pour les autres services/repositories

# Placeholder dependency function for variant repository (as before)
from src.product_variants.interfaces.repositories import AbstractProductVariantRepository # Use the actual path

logger = logging.getLogger(__name__)

# --- Remove Old CRUD Dependencies ---
# def get_quote_crud(...): ...
# QuoteCRUDDep = ...
# def get_quote_item_crud(...): ...
# QuoteItemCRUDDep = ...

# --- Dépendances Repository ---

def get_quote_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> AbstractQuoteRepository:
    """
    Fournit une instance du repository de devis (implémentation SQLAlchemy).
    
    Args:
        session: Session de base de données asynchrone.
        
    Returns:
        AbstractQuoteRepository: Instance du repository de devis.
    """
    logger.debug("Fourniture de SQLAlchemyQuoteRepository")
    return SQLAlchemyQuoteRepository(db_session=session)

QuoteRepositoryDep = Annotated[AbstractQuoteRepository, Depends(get_quote_repository)]


# --- Update Variant Repository Dependency (ensure it's correct) ---
# Assuming get_product_variant_repository is the correct provider function
VariantRepositoryDep = Annotated[AbstractProductVariantRepository, Depends(AbstractProductVariantRepository)]


# --- Dépendances Service ---

def get_quote_service(
    quote_repo: QuoteRepositoryDep,
    variant_repo: VariantRepositoryDep 
    # Remove db: Annotated[AsyncSession, Depends(get_db_session)] if service no longer needs it directly
) -> QuoteService:
    """
    Fournit une instance du service de gestion des devis.
    
    Args:
        quote_repo: Instance du repository de devis.
        variant_repo: Instance du repository de variants de produits.
        
    Returns:
        QuoteService: Instance du service de gestion des devis.
    """
    logger.debug("Fourniture de QuoteService avec repositories")
    # The QuoteService constructor will need to be updated to accept repositories
    return QuoteService(
        quote_repo=quote_repo,
        variant_repo=variant_repo 
        # Remove db=db if constructor changes
    )

QuoteServiceDep = Annotated[QuoteService, Depends(get_quote_service)]
