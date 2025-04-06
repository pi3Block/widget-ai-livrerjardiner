from typing import Optional, List, Any, Dict
from datetime import datetime
from decimal import Decimal # Gardé pour les types SQLAlchemy Numeric

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

class StockDB(Base):
    __tablename__ = "stock"

    product_variant_id: Mapped[int] = mapped_column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), primary_key=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation One-to-One vers ProductVariantDB
    variant: Mapped["ProductVariantDB"] = relationship(back_populates="stock")

class StockMovementDB(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_variant_id: Mapped[int] = mapped_column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), index=True, nullable=False)
    order_item_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("order_items.id", ondelete="SET NULL"), index=True)
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    movement_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    related_order_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relation Many-to-One vers ProductVariantDB
    variant: Mapped["ProductVariantDB"] = relationship(back_populates="stock_movements")
    # Relation Many-to-One vers OrderItemDB (si besoin)
    order_item: Mapped[Optional["OrderItemDB"]] = relationship(back_populates="stock_movements")

class QuoteDB(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    total_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relation Many-to-One vers UserDB
    user: Mapped["UserDB"] = relationship(back_populates="quotes")
    # Relation One-to-Many vers QuoteItemDB
    items: Mapped[List["QuoteItemDB"]] = relationship(back_populates="quote", cascade="all, delete-orphan")

class QuoteItemDB(Base):
    __tablename__ = "quote_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quote_id: Mapped[int] = mapped_column(Integer, ForeignKey("quotes.id", ondelete="CASCADE"), index=True, nullable=False)
    product_variant_id: Mapped[int] = mapped_column(Integer, ForeignKey("product_variants.id", ondelete="RESTRICT"), index=True, nullable=False) # RESTRICT pour éviter suppression si utilisé
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relation Many-to-One vers QuoteDB
    quote: Mapped["QuoteDB"] = relationship(back_populates="items")
    # Relation Many-to-One vers ProductVariantDB
    variant: Mapped["ProductVariantDB"] = relationship(back_populates="quote_items")

class OrderDB(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    delivery_address_id: Mapped[int] = mapped_column(Integer, ForeignKey("addresses.id", ondelete="RESTRICT"), index=True, nullable=False)
    billing_address_id: Mapped[int] = mapped_column(Integer, ForeignKey("addresses.id", ondelete="RESTRICT"), index=True, nullable=False)
    shipping_method: Mapped[Optional[str]] = mapped_column(String(100))
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relation Many-to-One vers UserDB
    user: Mapped["UserDB"] = relationship(back_populates="orders")
    # Relation Many-to-One vers AddressDB (Delivery)
    delivery_address: Mapped["AddressDB"] = relationship(back_populates="delivery_orders", foreign_keys=[delivery_address_id])
    # Relation Many-to-One vers AddressDB (Billing)
    billing_address: Mapped["AddressDB"] = relationship(back_populates="billing_orders", foreign_keys=[billing_address_id])
    # Relation One-to-Many vers OrderItemDB
    items: Mapped[List["OrderItemDB"]] = relationship(back_populates="order", cascade="all, delete-orphan")

class OrderItemDB(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    product_variant_id: Mapped[int] = mapped_column(Integer, ForeignKey("product_variants.id", ondelete="RESTRICT"), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relation Many-to-One vers OrderDB
    order: Mapped["OrderDB"] = relationship(back_populates="items")
    # Relation Many-to-One vers ProductVariantDB
    variant: Mapped["ProductVariantDB"] = relationship(back_populates="order_items")
    # Relation One-to-Many vers StockMovementDB
    stock_movements: Mapped[List["StockMovementDB"]] = relationship(back_populates="order_item")
