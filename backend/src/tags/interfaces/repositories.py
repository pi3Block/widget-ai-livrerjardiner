"""
Interfaces pour les repositories de tags.

Ce fichier contient les interfaces (classes abstraites) pour les repositories
utilisés dans le module tags.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple

from src.tags.models import Tag


class AbstractTagRepository(ABC):
    """Interface pour le repository des Tags."""
    
    @abstractmethod
    async def get_by_id(self, tag_id: int) -> Optional[Tag]:
        """Récupère une Tag par son ID."""
        pass
    
    @abstractmethod
    async def create(self, tag_data: Dict[str, Any]) -> Tag:
        """Crée une nouvelle Tag."""
        pass
    
    @abstractmethod
    async def update(self, tag_id: int, tag_data: Dict[str, Any]) -> Optional[Tag]:
        """Met à jour une Tag existante."""
        pass
    
    @abstractmethod
    async def delete(self, tag_id: int) -> Optional[Tag]:
        """Supprime une Tag."""
        pass
