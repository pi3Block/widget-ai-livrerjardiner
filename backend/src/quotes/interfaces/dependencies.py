import logging
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Correction de l'import pour get_db_session
from ...core.database import get_db_session

# Repositories
from src.quotes.domain.repositories import AbstractQuoteRepository
from src.quotes.infrastructure.persistence import SQLAlchemyQuoteRepository
# Besoin du repo variante pour le service
from src.products.interfaces.dependencies import VariantRepositoryDep 

# Services
from src.quotes.application.services import QuoteService

logger = logging.getLogger(__name__)

# --- Dépendances Repository ---
def get_quote_repository(db: AsyncSession = Depends(get_db_session)) -> AbstractQuoteRepository:
    """Injecte SQLAlchemyQuoteRepository."""
    logger.debug("Fourniture de SQLAlchemyQuoteRepository")
    return SQLAlchemyQuoteRepository(session=db)

QuoteRepositoryDep = Annotated[AbstractQuoteRepository, Depends(get_quote_repository)]

# --- Dépendances Service ---
def get_quote_service(
    quote_repo: QuoteRepositoryDep,
    variant_repo: VariantRepositoryDep # Injecté depuis le domaine products
) -> QuoteService:
    """Injecte QuoteService avec ses dépendances."""
    logger.debug("Fourniture de QuoteService")
    return QuoteService(quote_repo=quote_repo, variant_repo=variant_repo)

QuoteServiceDep = Annotated[QuoteService, Depends(get_quote_service)] 