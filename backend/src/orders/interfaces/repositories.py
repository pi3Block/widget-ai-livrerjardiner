from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any

# Import ORM models and API schemas needed for type hinting
from src.orders.models import Order, OrderItem, OrderCreate, OrderUpdate, OrderRead, OrderItemCreate


class AbstractOrderRepository(ABC):
    """Interface abstraite pour le repository des commandes et de leurs lignes."""

    @abstractmethod
    async def get_by_id(self, order_id: int) -> Optional[Order]:
        """Récupère une commande par son ID (modèle ORM)."""
        pass

    @abstractmethod
    async def get_by_id_as_read_schema(self, order_id: int) -> Optional[OrderRead]:
        """Récupère une commande par son ID (schéma Read avec items)."""
        # Note: L'implémentation devra charger les relations (items, adresses)
        pass

    @abstractmethod
    async def list_by_user(self, user_id: int, limit: int, offset: int) -> Tuple[List[OrderRead], int]:
        """Liste les commandes pour un utilisateur (schéma Read avec items)."""
        # Note: L'implémentation devra charger les relations et gérer la pagination
        pass

    @abstractmethod
    async def create_order_with_items(
        self, 
        order_data: Dict[str, Any], # Données pour l'Order (ex: user_id, total, adresses, etc.)
        items_data: List[Dict[str, Any]] # Données pour les OrderItems (variant_id, qty, price)
    ) -> Order:
        """Crée une commande et ses lignes associées de manière atomique. Retourne l'Order ORM créé."""
        # L'implémentation gérera la transaction
        pass

    @abstractmethod
    async def update_order_status(self, order_id: int, status: str) -> Optional[Order]:
        """Met à jour le statut d'une commande. Retourne l'Order ORM mis à jour."""
        pass

    # Potentiellement d'autres méthodes si nécessaire, par exemple:
    # @abstractmethod
    # async def get_order_items(self, order_id: int) -> List[OrderItem]:
    #     """Récupère uniquement les lignes d'une commande."""
    #     pass 