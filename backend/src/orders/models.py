from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from sqlmodel import SQLModel, Field, Relationship

# Forward references pour les relations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.users.models import User
    from src.addresses.models import Address
    from src.product_variants.models import ProductVariant

# --- Modèles de base pour OrderItem ---

class OrderItemBase(SQLModel):
    """Base pour les champs de la table OrderItem."""
    quantity: int = Field(..., gt=0)
    # Prix figé au moment de la commande
    price_at_order: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)
    product_variant_id: int = Field(foreign_key="product_variants.id", index=True)
    order_id: int = Field(foreign_key="orders.id", index=True)

class OrderItem(OrderItemBase, table=True):
    """Modèle de table pour les lignes de commande."""
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    # Relations
    order: "Order" = Relationship(back_populates="items")
    product_variant: "ProductVariant" = Relationship(back_populates="order_items")

    __tablename__ = "order_items"

# --- Modèles de base pour Order ---

class OrderBase(SQLModel):
    """Base pour les champs de la table Order."""
    status: str = Field(default="pending", max_length=50, index=True)
    total_amount: Decimal = Field(decimal_places=2, max_digits=12)
    delivery_address_id: int = Field(foreign_key="addresses.id", index=True)
    billing_address_id: int = Field(foreign_key="addresses.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)

class Order(OrderBase, table=True):
    """Modèle de table pour les commandes."""
    id: Optional[int] = Field(default=None, primary_key=True)
    order_date: Optional[datetime] = Field(default=None)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    # Relations
    user: "User" = Relationship(back_populates="orders")
    items: List["OrderItem"] = Relationship(back_populates="order")
    delivery_address: "Address" = Relationship(
        back_populates=None,
        sa_relationship_kwargs={"foreign_keys": "[Order.delivery_address_id]", "lazy": "joined"}
    )
    billing_address: "Address" = Relationship(
        back_populates=None,
        sa_relationship_kwargs={"foreign_keys": "[Order.billing_address_id]", "lazy": "joined"}
    )

    __tablename__ = "orders"

# --- Schémas API pour OrderItem ---

class OrderItemCreate(SQLModel):
    """Schéma pour la création d'un OrderItem."""
    product_variant_id: int
    quantity: int = Field(..., gt=0)
    # Le prix sera calculé par le service, pas fourni par l'API

class OrderItemResponse(SQLModel):
    """Schéma pour la réponse d'un OrderItem."""
    id: int
    order_id: int
    product_variant_id: int
    quantity: int
    price_at_order: Decimal
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Schémas API pour Order ---

class OrderCreate(SQLModel):
    """Schéma pour la création d'une Order."""
    delivery_address_id: int
    billing_address_id: int
    items: List[OrderItemCreate]
    # Le status et total_amount seront gérés par le service

class OrderUpdate(SQLModel):
    """Schéma pour la mise à jour d'une Order."""
    status: str = Field(..., max_length=50)

class OrderResponse(SQLModel):
    """Schéma pour la réponse d'une Order."""
    id: int
    user_id: int
    status: str
    total_amount: Decimal
    delivery_address_id: int
    billing_address_id: int
    order_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True

class PaginatedOrderResponse(SQLModel):
    """Schéma pour la réponse paginée d'une liste d'Orders."""
    items: List[OrderResponse]
    total: int 