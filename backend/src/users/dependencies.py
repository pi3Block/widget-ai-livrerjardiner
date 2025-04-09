"""
Module définissant les dépendances FastAPI pour le module utilisateur.

Fournit des instances de FastCRUD pour le modèle User, et le service
UserService injecté avec les dépendances nécessaires (session DB, CRUD).
"""
import logging
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastcrud import FastCRUD
# Import SQLModel base and missing user schemas
from sqlmodel import SQLModel
from src.users.models import User, UserCreate, UserUpdate, UserRead
from src.users.service import UserService

# Importation de la dépendance de session globale (à adapter si nécessaire)
from src.database import get_db_session

logger = logging.getLogger(__name__)

# Type hint pour la dépendance de session DB
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

# Dépendance pour obtenir le CRUD spécifique à User
def get_user_crud(session: DbSessionDep) -> FastCRUD[User, UserCreate, UserUpdate, UserUpdate, SQLModel, UserRead]:
    """
    Fournit une instance de FastCRUD typée pour le modèle User.
    
    Args:
        session: Session de base de données asynchrone
        
    Returns:
        FastCRUD[User, UserCreate, UserUpdate, UserUpdate, SQLModel, UserRead]: 
            Instance de FastCRUD configurée pour le modèle User avec ses schémas
    """
    logger.debug("Fourniture de FastCRUD[User, UserCreate, UserUpdate, UserUpdate, SQLModel, UserRead]")
    # Note: FastCRUD initialization only needs the model and session
    return FastCRUD(User, session)

# Type hint pour l'injection du CRUD User
UserCrudDep = Annotated[FastCRUD[User, UserCreate, UserUpdate, UserUpdate, SQLModel, UserRead], Depends(get_user_crud)]

# Dépendance pour obtenir le service utilisateur
def get_user_service(
    user_crud: UserCrudDep,
    db: DbSessionDep
) -> UserService:
    """
    Fournit une instance du service de gestion des utilisateurs.
    
    Args:
        user_crud: Instance de FastCRUD pour le modèle User
        db: Session de base de données asynchrone
        
    Returns:
        UserService: Instance du service de gestion des utilisateurs
    """
    logger.debug("Fourniture de UserService")
    return UserService(user_crud=user_crud, db=db) 