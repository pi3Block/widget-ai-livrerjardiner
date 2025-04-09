from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

# Forward reference
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.product_variants.models import ProductVariant # Ajuster l'import
    from src.orders.models import OrderItem # Ajuster l'import

# --- Modèle StockMovement SQLModel ---

class StockMovementBase(SQLModel):
    product_variant_id: int = Field(foreign_key="product_variants.id", index=True)
    quantity_change: int
    movement_type: str = Field(max_length=50)
    order_item_id: Optional[int] = Field(default=None, foreign_key="order_items.id", index=True)

class StockMovement(StockMovementBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)

    # Relations
    variant: "ProductVariant" = Relationship(back_populates="stock_movements")
    order_item: Optional["OrderItem"] = Relationship(back_populates="stock_movements") # Relation vers OrderItem

    __tablename__ = "stock_movements"

# Schémas API pour StockMovement
class StockMovementCreate(StockMovementBase):
    pass

class StockMovementRead(StockMovementBase):
    id: int
    created_at: datetime
    # Ajouter les relations si nécessaire pour la lecture
    # variant: Optional["ProductVariantRead"] = None
    # order_item: Optional["OrderItemRead"] = None

# --- Fin Modèle StockMovement SQLModel --- 