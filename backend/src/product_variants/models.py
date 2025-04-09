from typing import Optional, List, Any, Dict
from decimal import Decimal
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from sqlalchemy import JSON # Garder pour sa_type

# Forward references pour les relations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.products.models import Product # Ajuster l'import
    from src.tags.models import Tag, TagRead # Ajuster l'import
    from src.stock.models import Stock, StockRead # Ajuster l'import
    from src.quotes.models import QuoteItem # Ajuster l'import
    from src.orders.models import OrderItem # Ajuster l'import
    from src.stock_movements.models import StockMovement # Ajuster l'import

# --- Modèle de Lien ProductVariant <-> Tag ---
class ProductVariantTagLink(SQLModel, table=True):
    product_variant_id: Optional[int] = Field(
        default=None, foreign_key="product_variants.id", primary_key=True
    )
    tag_id: Optional[int] = Field(
        default=None, foreign_key="tags.id", primary_key=True
    )
    __tablename__ = "product_variant_tags"

# --- Fin Modèle de Lien ---


# --- Modèle ProductVariant SQLModel ---

class ProductVariantBase(SQLModel):
    sku: str = Field(index=True, unique=True, max_length=100)
    attributes: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)
    price: Decimal = Field(decimal_places=2, max_digits=10)
    image_url: Optional[str] = Field(default=None, max_length=255)
    product_id: int = Field(foreign_key="products.id", index=True)
    variant_description: Optional[str] = None
    cost_price: Optional[float] = None
    weight: Optional[float] = None
    is_active: bool = Field(default=True)

class ProductVariant(ProductVariantBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: Optional[datetime] = Field(default=None, sa_column_kwargs={"onupdate": datetime.utcnow})

    product: "Product" = Relationship(back_populates="variants")
    tags: List["Tag"] = Relationship(back_populates="product_variants", link_model=ProductVariantTagLink)
    stock: Optional["Stock"] = Relationship(back_populates="variant", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}) # One-to-one with stock

    # Relations One-to-Many vers SQLModel
    quote_items: List["QuoteItem"] = Relationship(back_populates="variant")
    order_items: List["OrderItem"] = Relationship(back_populates="variant")
    stock_movements: List["StockMovement"] = Relationship(back_populates="variant")

    __tablename__ = "product_variants"

# Schémas API pour ProductVariant
class ProductVariantCreate(ProductVariantBase):
    tag_ids: Optional[List[int]] = None # For linking tags on creation
    initial_stock: Optional[int] = None # For setting initial stock level

class ProductVariantRead(ProductVariantBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Stock is added dynamically by the service, not part of the base DB model read
    stock: Optional["StockRead"] = None # Field for the service to populate
    tags: List["TagRead"] = [] # Use TagRead schema

class ProductVariantReadWithStockAndTags(ProductVariantRead):
    # Already includes stock and tags from ProductVariantRead inheritance
    pass

class ProductVariantUpdate(SQLModel):
    sku: Optional[str] = None
    variant_description: Optional[str] = None
    price: Optional[Decimal] = None
    cost_price: Optional[float] = None
    weight: Optional[float] = None
    is_active: Optional[bool] = None
    attributes: Optional[Dict[str, Any]] = None
    tag_ids: Optional[List[int]] = None # For updating linked tags

# --- Fin Modèle ProductVariant SQLModel --- 