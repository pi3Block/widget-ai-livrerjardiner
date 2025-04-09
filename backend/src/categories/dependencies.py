import logging
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
# Supprimer FastCRUD si plus utilisé directement pour l'injection du service
# from fastcrud import FastCRUD

from src.database import get_db_session
# Supprimer l'import du modèle Category si plus nécessaire ici
# from src.categories.models import Category
from src.categories.service import CategoryService
# Importer l'interface et l'implémentation du Repository
from src.categories.interfaces.repositories import AbstractCategoryRepository
from src.categories.repositories import SQLAlchemyCategoryRepository

logger = logging.getLogger(__name__)

# Dependency for DB Session
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]

# --- Dépendance pour le Repository --- 
def get_category_repository(session: SessionDep) -> AbstractCategoryRepository:
    """
    Fournit une instance du repository de catégories.
    """
    logger.debug("Providing SQLAlchemyCategoryRepository")
    return SQLAlchemyCategoryRepository(db_session=session)

CategoryRepositoryDep = Annotated[AbstractCategoryRepository, Depends(get_category_repository)]

# --- Supprimer la dépendance get_category_crud --- 
# def get_category_crud(...)
# CategoryCRUDDep = ...

# --- Mettre à jour la dépendance Service Category --- 
def get_category_service(
    # Injecter le Repository via sa dépendance
    repository: CategoryRepositoryDep,
    # Supprimer db: SessionDep si le service ne l'utilise plus directement
) -> CategoryService:
    """
    Fournit une instance du service de gestion des catégories.

    Args:
        repository: Instance du repository de catégories.

    Returns:
        CategoryService: Instance du service de gestion des catégories.
    """
    logger.debug("Providing CategoryService with injected repository")
    # Passer le repository au constructeur du service
    return CategoryService(repository=repository)

CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)] 