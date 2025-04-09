from abc import ABC, abstractmethod
from typing import List, Optional
from src.quotes.models import Quote, QuoteCreate, QuoteUpdate

class AbstractQuoteRepository(ABC):
    """Interface abstraite pour le repository des devis."""
    
    @abstractmethod
    async def create(self, quote: QuoteCreate) -> Quote:
        """Crée un nouveau devis."""
        pass
        
    @abstractmethod
    async def get_by_id(self, quote_id: int) -> Optional[Quote]:
        """Récupère un devis par son ID."""
        pass
        
    @abstractmethod
    async def list_by_user(self, user_id: int, limit: int, offset: int) -> tuple[List[Quote], int]:
        """Liste les devis d'un utilisateur avec pagination."""
        pass
        
    @abstractmethod
    async def update(self, quote_id: int, quote_update: QuoteUpdate) -> Optional[Quote]:
        """Met à jour un devis."""
        pass
        
    @abstractmethod
    async def delete(self, quote_id: int) -> bool:
        """Supprime un devis."""
        pass 