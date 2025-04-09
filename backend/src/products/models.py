from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime # Assurer que cet import est présent et non commenté
# Supprimer les imports spécifiques aux variants et tags non utilisés directement ici
# from decimal import Decimal
# from pydantic import ConfigDict
# from sqlalchemy import JSON

# Forward references pour les relations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.categories.models import Category, CategoryRead # Ajuster l'import
    # Importer les variants depuis leur nouveau module
    from src.product_variants.models import ProductVariant, ProductVariantRead, ProductVariantReadWithStockAndTags
    # Importer TagRead si nécessaire dans les schémas Product (sinon supprimer)
    # from src.tags.models import TagRead
    # Les autres relations (Stock, QuoteItem, OrderItem, StockMovement) sont sur ProductVariant, pas Product

# --- Modèle Product SQLModel ---

class ProductBase(SQLModel):
    name: str = Field(index=True, max_length=255)
    base_description: Optional[str] = Field(default=None)
    slug: Optional[str] = Field(default=None, index=True, unique=True, max_length=255)
    category_id: Optional[int] = Field(default=None, foreign_key="categories.id", index=True)
    is_active: bool = Field(default=True)
    meta_title: Optional[str] = Field(default=None)
    meta_description: Optional[str] = Field(default=None)

class Product(ProductBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: Optional[datetime] = Field(default=None, sa_column_kwargs={"onupdate": datetime.utcnow})

    category: Optional["Category"] = Relationship(back_populates="products")
    variants: List["ProductVariant"] = Relationship(back_populates="product", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    __tablename__ = "products"

# Schémas API pour Product
class ProductCreate(ProductBase):
    # tag_ids était lié aux variants, le service ProductVariant gère ça maintenant
    pass

class ProductRead(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    category: Optional["CategoryRead"] = None # Utiliser le schéma Read de Category
    variants: List["ProductVariantRead"] = [] # Utiliser le schéma Read de ProductVariant

class ProductReadWithDetails(ProductRead):
    # Utiliser le schéma CategoryReadWithDetails si défini, sinon CategoryRead
    # category: Optional["CategoryReadWithDetails"] = None
    variants: List["ProductVariantReadWithStockAndTags"] = [] # Utiliser le schéma détaillé de ProductVariant

class ProductUpdate(SQLModel):
    name: Optional[str] = None
    base_description: Optional[str] = None
    slug: Optional[str] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    # tag_ids était lié aux variants, supprimer ici

# --- Fin Modèle Product SQLModel --- 