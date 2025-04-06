from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from .entities import Quote

class AbstractQuoteRepository(ABC):
    """Interface abstraite pour le repository des Devis."""

    @abstractmethod
    async def get_by_id(self, quote_id: int) -> Optional[Quote]:
        """Récupère un devis par son ID, incluant ses items."""
        raise NotImplementedError

    @abstractmethod
    async def list_for_user(self, user_id: int, limit: int, offset: int) -> List[Quote]:
        """Liste les devis pour un utilisateur donné avec pagination."""
        raise NotImplementedError
    
    @abstractmethod
    async def add(self, quote_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Quote:
        """Ajoute un nouveau devis avec ses items."""
        # Prend les données brutes (dicts) pour la flexibilité
        raise NotImplementedError

    @abstractmethod
    async def update_status(self, quote_id: int, status: str) -> Optional[Quote]:
        """Met à jour le statut d'un devis."""
        raise NotImplementedError
    
    # Ajouter d'autres méthodes si nécessaire (ex: delete, list_all_admin, ...) 