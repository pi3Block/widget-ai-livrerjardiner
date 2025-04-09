"""Interfaces pour les repositories d'adresses.

Ce fichier contient les interfaces (classes abstraites) pour les repositories
utilisés dans le module addresses.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple

from src.addresses.models import Address, AddressList


class AbstractAddressRepository(ABC):
    """Interface pour le repository des adresses."""
    
    @abstractmethod
    async def get_by_id(self, address_id: int) -> Optional[Address]:
        """Récupère une adresse par son ID."""
        pass
    
    @abstractmethod
    async def get_by_user_id(self, user_id: int, skip: int = 0, limit: int = 1000) -> AddressList:
        """Liste les adresses pour un utilisateur donné avec pagination et retourne le total."""
        pass
    
    @abstractmethod
    async def create(self, address_data: Dict[str, Any]) -> Address:
        """Crée une nouvelle adresse."""
        pass
    
    @abstractmethod
    async def update(self, address_id: int, address_data: Dict[str, Any]) -> Optional[Address]:
        """Met à jour une adresse existante."""
        pass
    
    @abstractmethod
    async def delete(self, address_id: int) -> Optional[Address]:
        """Supprime une adresse."""
        pass
    
    @abstractmethod
    async def set_default(self, address_id: int, user_id: int) -> None:
        """Définit une adresse comme étant l'adresse par défaut."""
        pass