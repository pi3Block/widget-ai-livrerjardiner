import abc
from typing import Optional, List

# Import de l'entité domaine
from src.users.domain.user_entity import UserEntity

class AbstractUserRepository(abc.ABC):
    """Interface abstraite pour le dépôt des utilisateurs."""

    @abc.abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[UserEntity]:
        """Récupère une entité utilisateur par son ID."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        """Récupère une entité utilisateur par son email."""
        raise NotImplementedError

    # Peut-être ajouter une méthode pour charger avec les adresses si c'est un cas d'usage fréquent
    @abc.abstractmethod
    async def get_by_id_with_addresses(self, user_id: int) -> Optional[UserEntity]:
        """Récupère une entité utilisateur par ID avec ses adresses associées."""
        # Note: La structure de UserEntity n'inclut pas directement les adresses.
        # Cette méthode pourrait retourner l'entité UserEntity et la logique
        # de récupération/association des adresses serait dans l'implémentation,
        # ou alors UserEntity devrait être adaptée pour contenir une liste optionnelle d'AddressEntity.
        # Pour l'instant, on définit la méthode, l'implémentation précisera.
        raise NotImplementedError

    @abc.abstractmethod
    async def add(self, user: UserEntity) -> UserEntity:
        """Ajoute une nouvelle entité utilisateur à la base de données."""
        # Note: L'entité passée ici pourrait ne pas avoir d'ID au début.
        # L'implémentation devra gérer le hachage du mot de passe.
        # La méthode retourne l'entité ajoutée (potentiellement avec l'ID assigné).
        raise NotImplementedError

    @abc.abstractmethod
    async def update(self, user: UserEntity) -> Optional[UserEntity]:
        """Met à jour une entité utilisateur existante."""
        # L'implémentation devra s'assurer que l'utilisateur existe.
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, user_id: int) -> bool:
        """Supprime un utilisateur par son ID."""
        raise NotImplementedError

    # On pourrait ajouter d'autres méthodes si nécessaire (ex: list_users, count_users)
