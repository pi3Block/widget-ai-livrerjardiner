from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field

# Entités du Domaine "Quotes"

class QuoteItem(BaseModel):
    id: int
    quote_id: int
    product_variant_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    # On pourrait charger la variante ici si nécessaire, mais gardons simple pour l'instant
    # product_variant: Optional[ProductVariant] = None 

    class Config:
        from_attributes = True

class Quote(BaseModel):
    id: int
    user_id: int
    status: str = Field(..., max_length=50) # Ex: 'pending', 'accepted', 'rejected', 'expired'
    created_at: datetime
    updated_at: datetime
    total_price: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=2) # Calculé

    items: List[QuoteItem] = []
    # user: Optional[UserEntity] = None # Charger si besoin via service

    class Config:
        from_attributes = True 