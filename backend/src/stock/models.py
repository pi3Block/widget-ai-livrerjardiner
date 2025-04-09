from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from pydantic import ConfigDict

# Forward references pour les relations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.product_variants.models import ProductVariant
    from src.orders.models import OrderItem
    # Ajouter ProductVariantRead, OrderItemRead si des schémas ReadWith... sont nécessaires

# --- Modèle Stock ---

# 1. Modèle de base (données communes)
class StockBase(SQLModel):
    quantity: int = Field(default=0)
    stock_alert_threshold: Optional[int] = Field(default=10)
    last_updated: Optional[datetime] = Field(default=None)

# 2. Modèle de table (hérite de Base)
class Stock(StockBase, table=True):
    product_variant_id: int = Field(foreign_key="product_variants.id", primary_key=True, index=True)
    
    # Relation One-to-One/Many vers ProductVariant
    variant: "ProductVariant" = Relationship(back_populates="stock")

    __tablename__ = "stock"
    model_config = ConfigDict(from_attributes=True)

# 3. Schémas API pour Stock
class StockRead(StockBase):
    product_variant_id: int
    model_config = ConfigDict(from_attributes=True)

class StockUpdate(SQLModel):
    quantity: Optional[int] = Field(default=None)
    stock_alert_threshold: Optional[int] = Field(default=None)

# Pas de StockCreate car géré via ProductVariant ou mouvements

# --- Modèle StockMovement ---

# 1. Modèle de base (données communes)
class StockMovementBase(SQLModel):
    quantity_change: int
    movement_type: str = Field(max_length=50)
    created_at: Optional[datetime] = Field(default=None)

# 2. Modèle de table (hérite de Base)
class StockMovement(StockMovementBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_variant_id: int = Field(foreign_key="product_variants.id", index=True)
    order_item_id: Optional[int] = Field(default=None, foreign_key="order_items.id", index=True)

    # Relations
    variant: "ProductVariant" = Relationship(back_populates="stock_movements")
    order_item: Optional["OrderItem"] = Relationship(back_populates="stock_movements")

    __tablename__ = "stock_movements"
    model_config = ConfigDict(from_attributes=True)

# 3. Schémas API pour StockMovement
class StockMovementCreate(SQLModel):
    quantity_change: int
    movement_type: str = Field(max_length=50)
    product_variant_id: int
    order_item_id: Optional[int] = None

class StockMovementRead(StockMovementBase):
    id: int
    product_variant_id: int
    order_item_id: Optional[int]
    model_config = ConfigDict(from_attributes=True)

# Pas de StockMovementUpdate car historique

# --- Fin Modèle StockMovement --- 