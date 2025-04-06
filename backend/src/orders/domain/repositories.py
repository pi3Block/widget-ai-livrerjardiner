from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from .entities import Order

class AbstractOrderRepository(ABC):
    """Interface abstraite pour le repository des Commandes."""

    @abstractmethod
    async def get_by_id(self, order_id: int) -> Optional[Order]:
        """Récupère une commande par son ID, incluant ses items et potentiellement adresses."""
        raise NotImplementedError

    @abstractmethod
    async def list_for_user(self, user_id: int, limit: int, offset: int) -> List[Order]:
        """Liste les commandes pour un utilisateur donné avec pagination."""
        raise NotImplementedError
    
    @abstractmethod
    async def add(self, order_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Order:
        """Ajoute une nouvelle commande avec ses items.
        NOTE: La décrémentation du stock n'est PAS gérée ici, mais dans le service.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_status(self, order_id: int, status: str) -> Optional[Order]:
        """Met à jour le statut d'une commande."""
        raise NotImplementedError
    
    # Ajouter d'autres méthodes si nécessaire (ex: delete, list_all_admin, ...) 