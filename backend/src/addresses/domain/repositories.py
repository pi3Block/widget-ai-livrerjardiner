import abc
from typing import Optional, List

# Import de l'entité domaine
from src.addresses.domain.address_entity import AddressEntity

class AbstractAddressRepository(abc.ABC):
    """Interface abstraite pour le dépôt des adresses."""

    @abc.abstractmethod
    async def get_by_id(self, address_id: int) -> Optional[AddressEntity]:
        """Récupère une entité adresse par son ID."""
        raise NotImplementedError

    @abc.abstractmethod
    async def list_by_user_id(self, user_id: int) -> List[AddressEntity]:
        """Liste toutes les adresses pour un utilisateur donné."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_default_by_user_id(self, user_id: int) -> Optional[AddressEntity]:
        """Récupère l'adresse par défaut pour un utilisateur donné."""
        raise NotImplementedError

    @abc.abstractmethod
    async def add(self, address: AddressEntity) -> AddressEntity:
        """Ajoute une nouvelle entité adresse."""
        raise NotImplementedError

    @abc.abstractmethod
    async def update(self, address: AddressEntity) -> Optional[AddressEntity]:
        """Met à jour une entité adresse existante."""
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, address_id: int) -> bool:
        """Supprime une adresse par son ID."""
        raise NotImplementedError

    @abc.abstractmethod
    async def set_default(self, user_id: int, address_id: int) -> bool:
        """Définit une adresse comme étant celle par défaut pour un utilisateur."""
        raise NotImplementedError 