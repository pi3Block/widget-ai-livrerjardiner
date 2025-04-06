from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field

# Entités du Domaine "Orders"

class OrderItem(BaseModel):
    id: int
    order_id: int
    product_variant_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2) # Prix au moment de la commande
    # product_variant: Optional[ProductVariant] = None # Charger si besoin

    class Config:
        from_attributes = True

class Order(BaseModel):
    id: int
    user_id: int
    status: str = Field(..., max_length=50) # Ex: 'pending', 'processing', 'shipped', 'delivered', 'cancelled'
    created_at: datetime
    updated_at: datetime
    total_price: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    delivery_address_id: int 
    billing_address_id: int
    # tracking_number: Optional[str] = None

    items: List[OrderItem] = []
    # delivery_address: Optional[Address] = None # Charger si besoin
    # billing_address: Optional[Address] = None # Charger si besoin
    # user: Optional[UserEntity] = None # Charger si besoin

    class Config:
        from_attributes = True 