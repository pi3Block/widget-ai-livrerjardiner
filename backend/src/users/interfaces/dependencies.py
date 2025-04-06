from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Importations nécessaires (chemins à vérifier/adapter)
from src.core.database import get_db_session # Supposé exister
from src.users.domain.repositories import AbstractUserRepository
from src.users.infrastructure.user_sql_repository import UserSQLRepository
from src.users.application.services import AuthService, UserService

# Dépendance pour obtenir le dépôt d'utilisateurs
def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> AbstractUserRepository:
    """Injecte l'implémentation SQL du dépôt utilisateur."""
    return UserSQLRepository(session=session)

# Dépendance pour obtenir le service d'authentification
def get_auth_service(
    user_repo: Annotated[AbstractUserRepository, Depends(get_user_repository)]
) -> AuthService:
    """Injecte le service d'authentification."""
    return AuthService(user_repo=user_repo)

# Dépendance pour obtenir le service utilisateur
def get_user_service(
    user_repo: Annotated[AbstractUserRepository, Depends(get_user_repository)]
) -> UserService:
    """Injecte le service utilisateur."""
    return UserService(user_repo=user_repo) 