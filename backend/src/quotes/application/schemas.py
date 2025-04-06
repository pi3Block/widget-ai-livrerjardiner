from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field

# --- Schémas pour QuoteItem ---

class QuoteItemBase(BaseModel):
    product_variant_id: int
    quantity: int = Field(..., gt=0)
    # Le prix unitaire peut être fourni ou récupéré depuis la variante produit
    unit_price: Optional[Decimal] = Field(None, gt=0, max_digits=10, decimal_places=2)

class QuoteItemCreate(QuoteItemBase):
    # Pour la création, le prix est généralement déterminé par le backend
    unit_price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)

class QuoteItemResponse(QuoteItemBase):
    id: int
    quote_id: int
    unit_price: Decimal # Assurer que le prix est toujours présent dans la réponse
    # Inclure la variante produit si nécessaire ?
    # product_variant: Optional[ProductVariantResponse] = None

    class Config:
        from_attributes = True

# --- Schémas pour Quote ---

class QuoteBase(BaseModel):
    # user_id sera déterminé par l'utilisateur authentifié ou fourni par l'admin
    status: Optional[str] = Field("pending", max_length=50, description="Statut initial du devis")
    # total_price est calculé

class QuoteCreate(QuoteBase):
    user_id: int # Requis pour la création
    items: List[QuoteItemCreate]

class QuoteUpdate(BaseModel):
    # Seul le statut peut être mis à jour via un endpoint dédié
    status: str = Field(..., max_length=50)

class QuoteResponse(QuoteBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    total_price: Optional[Decimal] = Field(None, description="Prix total calculé")
    items: List[QuoteItemResponse] = []
    # Inclure l'utilisateur ?
    # user: Optional[UserResponse] = None 
    status: str # Assurer que le statut est toujours présent

    class Config:
        from_attributes = True

class PaginatedQuoteResponse(BaseModel):
    items: List[QuoteResponse]
    total: int 