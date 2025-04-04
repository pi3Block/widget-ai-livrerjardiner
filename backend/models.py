from pydantic import BaseModel, EmailStr, Field, Json
from typing import Optional, List, Any, Dict
from datetime import datetime
from decimal import Decimal # Pour les prix

# Imports SQLAlchemy
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Numeric,
    Table # Pour les tables d'association Many-to-Many
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func # Pour CURRENT_TIMESTAMP

# Import de la Base déclarative depuis database.py
from database import Base

# ======================================================
# Models SQLAlchemy (Basés sur table.sql)
# ======================================================

# Table d'association pour ProductVariant <-> Tag (Many-to-Many)
product_variant_tags_table = Table(
    "product_variant_tags",
    Base.metadata,
    Column("product_variant_id", Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(100))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation One-to-Many vers AddressDB
    addresses: Mapped[List["AddressDB"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    # Relations vers OrderDB et QuoteDB (si besoin de naviguer depuis User)
    orders: Mapped[List["OrderDB"]] = relationship(back_populates="user")
    quotes: Mapped[List["QuoteDB"]] = relationship(back_populates="user")

class AddressDB(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    street: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation Many-to-One vers UserDB
    user: Mapped["UserDB"] = relationship(back_populates="addresses")
    # Relations vers OrderDB (si besoin)
    delivery_orders: Mapped[List["OrderDB"]] = relationship(back_populates="delivery_address", foreign_keys="[OrderDB.delivery_address_id]")
    billing_orders: Mapped[List["OrderDB"]] = relationship(back_populates="billing_address", foreign_keys="[OrderDB.billing_address_id]")

class CategoryDB(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    parent_category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation self-referential pour parent/enfants
    parent: Mapped[Optional["CategoryDB"]] = relationship(back_populates="children", remote_side=[id])
    children: Mapped[List["CategoryDB"]] = relationship(back_populates="parent", cascade="all, delete-orphan")
    # Relation One-to-Many vers ProductDB
    products: Mapped[List["ProductDB"]] = relationship(back_populates="category")

class ProductDB(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True) # index=True basé sur idx_products_name
    base_description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation Many-to-One vers CategoryDB
    category: Mapped[Optional["CategoryDB"]] = relationship(back_populates="products")
    # Relation One-to-Many vers ProductVariantDB
    variants: Mapped[List["ProductVariantDB"]] = relationship(back_populates="product", cascade="all, delete-orphan")

class TagDB(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    # Relation Many-to-Many vers ProductVariantDB via la table d'association
    product_variants: Mapped[List["ProductVariantDB"]] = relationship(
        secondary=product_variant_tags_table,
        back_populates="tags"
    )

class ProductVariantDB(Base):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    # Utiliser JSONB pour PostgreSQL
    attributes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    # Utiliser Numeric pour DECIMAL
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation Many-to-One vers ProductDB
    product: Mapped["ProductDB"] = relationship(back_populates="variants")
    # Relation Many-to-Many vers TagDB via la table d'association
    tags: Mapped[List["TagDB"]] = relationship(
        secondary=product_variant_tags_table,
        back_populates="product_variants"
    )
    # Relation One-to-One vers StockDB
    stock: Mapped[Optional["StockDB"]] = relationship(back_populates="variant", uselist=False, cascade="all, delete-orphan")
    # Relation One-to-Many vers QuoteItemDB et OrderItemDB
    quote_items: Mapped[List["QuoteItemDB"]] = relationship(back_populates="variant")
    order_items: Mapped[List["OrderItemDB"]] = relationship(back_populates="variant")
    # Relation One-to-Many vers StockMovementDB
    stock_movements: Mapped[List["StockMovementDB"]] = relationship(back_populates="variant")

# ======================================================
# Models Pydantic (Utilisés pour l'API et la validation)
# ======================================================

# Configuration commune pour activer ORM mode (renommé en from_attributes)
class OrmBaseModel(BaseModel):
    class Config:
        # orm_mode = True
        from_attributes = True # Remplacer orm_mode

# ======================================================
# Models: Users & Addresses
# ======================================================

class AddressBase(OrmBaseModel):
    street: str
    city: str
    zip_code: str
    country: str
    is_default: bool = False

class AddressCreate(AddressBase):
    pass

class AddressUpdate(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

class AddressDBBase(AddressBase):
    id: int
    user_id: int
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )

class AddressDB(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    street: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100))
    zip_code: Mapped[str] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(100))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation inverse
    user: Mapped["UserDB"] = relationship(back_populates="addresses")

    # Relation pour les commandes (livraison)
    delivery_orders: Mapped[List["OrderDB"]] = relationship("OrderDB", back_populates="delivery_address", foreign_keys="OrderDB.delivery_address_id")
    # Relation pour les commandes (facturation)
    billing_orders: Mapped[List["OrderDB"]] = relationship("OrderDB", back_populates="billing_address", foreign_keys="OrderDB.billing_address_id")

class UserBase(OrmBaseModel):
    email: EmailStr
    name: Optional[str] = None

class UserCreate(UserBase):
    password: str # Mot de passe en clair lors de la création/login

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    addresses: List[AddressDBBase] = [] # Relation chargée via ORM

# ======================================================
# Models: Categories & Tags
# ======================================================

class CategoryBase(OrmBaseModel):
    name: str
    description: Optional[str] = None
    parent_category_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # Pourrait avoir sub_categories: List['Category'] = [] si nécessaire

class TagBase(OrmBaseModel):
    name: str

class TagCreate(TagBase):
    pass

class Tag(TagBase):
    id: int

# ======================================================
# Models: Products & Variants
# ======================================================

class ProductBase(OrmBaseModel):
    name: str
    base_description: Optional[str] = None
    category_id: Optional[int] = None

class ProductCreate(ProductBase):
    pass

# Modèle pour les variations de produit
class ProductVariantBase(OrmBaseModel):
    sku: str = Field(..., description="Référence unique (SKU) de la variation")
    attributes: Optional[Dict[str, Any]] = None # ex: {'size': 'M', 'color': 'Red'}
    price: Decimal
    image_url: Optional[str] = None

class ProductVariantCreate(ProductVariantBase):
    product_id: int # Nécessaire à la création
    initial_stock: Optional[int] = Field(0, description="Stock initial lors de la création de la variation")
    stock_alert_threshold: Optional[int] = 10

class ProductVariant(ProductVariantBase):
    id: int
    product_id: int
    created_at: datetime
    updated_at: datetime
    tags: List[Tag] = [] # Relation chargée via ORM

# Modèle complet du produit avec ses variations
class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    category: Optional[Category] = None # Relation chargée
    variants: List[ProductVariant] = [] # Relation chargée

# ======================================================
# Models: Stock & Stock Movements
# ======================================================

class StockBase(OrmBaseModel):
    quantity: int
    stock_alert_threshold: Optional[int] = 10

class Stock(StockBase):
    product_variant_id: int # Clé primaire et étrangère
    last_updated: datetime
    variant: ProductVariant # Relation chargée (optionnel)

# Pas besoin de StockCreate séparé, géré lors de la création de Variant ou via endpoint /restock

class StockMovementBase(OrmBaseModel):
    product_variant_id: int
    quantity_change: int
    movement_type: str # Corresponds à la colonne SQL
    order_item_id: Optional[int] = None

class StockMovementCreate(StockMovementBase):
    pass

class StockMovement(StockMovementBase):
    id: int
    created_at: datetime
    # variant: ProductVariant # Relation chargée (optionnel)

# ======================================================
# Models: Quotes & Quote Items
# ======================================================

class QuoteItemBase(OrmBaseModel):
    product_variant_id: int
    quantity: int
    price_at_quote: Decimal

class QuoteItemCreate(QuoteItemBase):
    pass # quote_id sera ajouté par le service

class QuoteItem(QuoteItemBase):
    id: int
    quote_id: int
    created_at: datetime
    updated_at: datetime
    variant: Optional[ProductVariant] = None # Relation chargée

class QuoteBase(OrmBaseModel):
    user_id: int
    status: str = 'pending'
    expires_at: Optional[datetime] = None

class QuoteCreate(QuoteBase):
    items: List[QuoteItemCreate] # Les items sont créés en même temps

class Quote(QuoteBase):
    id: int
    quote_date: datetime
    created_at: datetime
    updated_at: datetime
    user: Optional[User] = None # Relation chargée
    items: List[QuoteItem] = [] # Relation chargée

# ======================================================
# Models: Orders & Order Items
# ======================================================

class OrderItemBase(OrmBaseModel):
    product_variant_id: int
    quantity: int
    price_at_order: Decimal

class OrderItemCreate(OrderItemBase):
    pass # order_id sera ajouté par le service

class OrderItem(OrderItemBase):
    id: int
    order_id: int
    created_at: datetime
    updated_at: datetime
    variant: Optional[ProductVariant] = None # Relation chargée

class OrderBase(OrmBaseModel):
    user_id: int
    status: str = 'pending'
    total_amount: Decimal
    delivery_address_id: int
    billing_address_id: int

class OrderCreate(OrderBase):
    items: List[OrderItemCreate] # Les items sont créés en même temps
    # delivery_method: str # Si on veut le garder en dehors de l'adresse ?

class Order(OrderBase):
    id: int
    order_date: datetime
    created_at: datetime
    updated_at: datetime
    user: Optional[User] = None # Relation chargée
    delivery_address: Optional[AddressDB] = None # Relation chargée
    billing_address: Optional[AddressDB] = None # Relation chargée
    items: List[OrderItem] = [] # Relation chargée

# ======================================================
# Models: Request Payloads (Exemples)
# ======================================================
# Ces modèles seront utilisés dans main.py pour les requêtes API

class CartItem(BaseModel):
    sku: str # L'utilisateur fournit le SKU de la variation
    quantity: int

class CreateQuoteRequest(BaseModel):
    user_email: EmailStr # Ou user_id si l'utilisateur est authentifié
    items: List[CartItem]

class CreateOrderRequest(BaseModel):
    user_email: EmailStr # Ou user_id si authentifié
    items: List[CartItem]
    delivery_address_id: int
    billing_address_id: int # Peut être le même que delivery
    # delivery_method: Optional[str] = "livraison"
    # payment_token: str # Exemple pour info paiement

# Mise à jour nécessaire pour les types ForwardRef si utilisation de relations circulaires poussée
# Category.update_forward_refs()
# Product.update_forward_refs()
# etc.

class StockDB(Base):
    __tablename__ = "stock"

    # Clé primaire est aussi clé étrangère
    product_variant_id: Mapped[int] = mapped_column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stock_alert_threshold: Mapped[Optional[int]] = mapped_column(Integer, default=10)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation One-to-One vers ProductVariantDB
    variant: Mapped["ProductVariantDB"] = relationship(back_populates="stock")

class StockMovementDB(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_variant_id: Mapped[int] = mapped_column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), index=True, nullable=False)
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Lien optionnel vers order_items
    order_item_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("order_items.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relation Many-to-One vers ProductVariantDB
    variant: Mapped["ProductVariantDB"] = relationship(back_populates="stock_movements")
    # Relation Many-to-One vers OrderItemDB (optionnelle)
    order_item: Mapped[Optional["OrderItemDB"]] = relationship(back_populates="stock_movements")

class QuoteDB(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    quote_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(50), nullable=False, default='pending', index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation Many-to-One vers UserDB
    user: Mapped["UserDB"] = relationship(back_populates="quotes")
    # Relation One-to-Many vers QuoteItemDB
    items: Mapped[List["QuoteItemDB"]] = relationship(back_populates="quote", cascade="all, delete-orphan")

class QuoteItemDB(Base):
    __tablename__ = "quote_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quote_id: Mapped[int] = mapped_column(Integer, ForeignKey("quotes.id", ondelete="CASCADE"), index=True, nullable=False)
    product_variant_id: Mapped[int] = mapped_column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_at_quote: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation Many-to-One vers QuoteDB
    quote: Mapped["QuoteDB"] = relationship(back_populates="items")
    # Relation Many-to-One vers ProductVariantDB
    variant: Mapped["ProductVariantDB"] = relationship(back_populates="quote_items")

class OrderDB(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default='pending', index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_address_id: Mapped[int] = mapped_column(Integer, ForeignKey("addresses.id", ondelete="RESTRICT"), nullable=False)
    billing_address_id: Mapped[int] = mapped_column(Integer, ForeignKey("addresses.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation Many-to-One vers UserDB
    user: Mapped["UserDB"] = relationship(back_populates="orders")
    # Relation Many-to-One vers AddressDB (livraison)
    delivery_address: Mapped["AddressDB"] = relationship(back_populates="delivery_orders", foreign_keys=[delivery_address_id])
    # Relation Many-to-One vers AddressDB (facturation)
    billing_address: Mapped["AddressDB"] = relationship(back_populates="billing_orders", foreign_keys=[billing_address_id])
    # Relation One-to-Many vers OrderItemDB
    items: Mapped[List["OrderItemDB"]] = relationship(back_populates="order", cascade="all, delete-orphan")

class OrderItemDB(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    # Utiliser RESTRICT comme dans le SQL
    product_variant_id: Mapped[int] = mapped_column(Integer, ForeignKey("product_variants.id", ondelete="RESTRICT"), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_at_order: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation Many-to-One vers OrderDB
    order: Mapped["OrderDB"] = relationship(back_populates="items")
    # Relation Many-to-One vers ProductVariantDB
    variant: Mapped["ProductVariantDB"] = relationship(back_populates="order_items")
    # Relation One-to-Many vers StockMovementDB (un OrderItem peut déclencher un mouvement)
    stock_movements: Mapped[List["StockMovementDB"]] = relationship(back_populates="order_item")
