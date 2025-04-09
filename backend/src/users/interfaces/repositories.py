from abc import ABC, abstractmethod
from typing import Optional

from src.users.models import User, UserRead  # Assuming models are in src/users/models.py


class AbstractUserRepository(ABC):
    """Interface abstraite pour le repository des utilisateurs."""

    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Récupère un utilisateur par son ID. Retourne le modèle de table."""
        pass

    @abstractmethod
    async def get_by_id_as_read_schema(self, user_id: int) -> Optional[UserRead]:
        """Récupère un utilisateur par son ID. Retourne le schéma de lecture UserRead."""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Récupère un utilisateur par son email. Retourne le modèle de table."""
        pass

    # Ajoutez d'autres méthodes abstraites si nécessaire (create, update, delete, list, etc.) 