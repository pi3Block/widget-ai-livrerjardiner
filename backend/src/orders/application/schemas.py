from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field

# --- Schémas pour OrderItem ---
# Similaires à QuoteItem, mais liés à une Order

class OrderItemBase(BaseModel):
    product_variant_id: int
    quantity: int = Field(..., gt=0)
    # Prix figé au moment de la commande
    unit_price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)

class OrderItemCreate(OrderItemBase):
    # Utilisé lors de la création de la commande
    pass

class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    # product_variant: Optional[ProductVariantResponse] = None # Inclure si besoin

    class Config:
        from_attributes = True

# --- Schémas pour Order ---

class OrderBase(BaseModel):
    # user_id sera déterminé par l'utilisateur authentifié
    status: Optional[str] = Field("pending", max_length=50, description="Statut initial de la commande")
    delivery_address_id: int 
    billing_address_id: int
    # total_price est calculé par le service

class OrderCreate(OrderBase):
    user_id: int # Requis pour la création
    items: List[OrderItemCreate]
    # Le total_price n'est PAS fourni par le client, il est calculé et validé par le backend

class OrderUpdate(BaseModel):
    # Seul le statut peut être mis à jour via un endpoint dédié (potentiellement d'autres champs par admin?)
    status: str = Field(..., max_length=50)

class OrderResponse(OrderBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    total_price: Decimal # Doit être présent dans la réponse
    items: List[OrderItemResponse] = []
    status: str # Statut final
    # Inclure les adresses et l'utilisateur ?
    # delivery_address: Optional[AddressResponse] = None 
    # billing_address: Optional[AddressResponse] = None
    # user: Optional[UserResponse] = None 

    class Config:
        from_attributes = True

class PaginatedOrderResponse(BaseModel):
    items: List[OrderResponse]
    total: int 