from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Dict, Any
from decimal import Decimal

from src.quotes.models import Quote, QuoteRead, QuoteCreate, QuoteItem, QuoteItemCreate, QuoteUpdate


class AbstractQuoteRepository(ABC):
    """Interface abstraite pour le repository des devis."""

    @abstractmethod
    async def get_by_id_with_items(self, *, quote_id: int) -> Optional[Quote]:
        """Récupère un devis par son ID, incluant ses items."""
        pass

    @abstractmethod
    async def list_by_user_id(self, *, user_id: int, offset: int = 0, limit: int = 100) -> Tuple[List[Quote], int]:
        """Liste les devis pour un utilisateur spécifique avec pagination."""
        pass
    
    @abstractmethod
    async def list_all(self, *, offset: int = 0, limit: int = 100) -> Tuple[List[Quote], int]:
        """Liste tous les devis avec pagination (pour admin par exemple)."""
        pass

    @abstractmethod
    async def create_with_items(self, *, quote_data: QuoteCreate) -> Quote:
        """Crée un nouveau devis avec ses items."""
        pass

    @abstractmethod
    async def update_status(self, *, quote_id: int, status_update: QuoteUpdate) -> Optional[Quote]:
        """Met à jour le statut d'un devis existant."""
        pass

    @abstractmethod
    async def delete_quote(self, *, quote_id: int) -> bool:
        """Supprime un devis et ses items associés."""
        pass

    # Potentiellement d'autres méthodes spécifiques si nécessaire
    # Par exemple: find_by_status, get_total_value, etc. 