from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl

# Schémas Pydantic pour la couche Application / API du domaine Products
# Ces schémas définissent les structures de données pour les requêtes et réponses API.

# --- Schémas pour Tag ---

class TagBase(BaseModel):
    name: str = Field(..., max_length=50)

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    id: int

    class Config:
        from_attributes = True

# --- Schémas pour Category ---

class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    parent_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    # Permet de mettre à jour tous les champs de Base
    pass

class CategoryResponse(CategoryBase):
    id: int
    # Ajouter des infos supplémentaires si besoin (ex: nombre de produits)

    class Config:
        from_attributes = True

# --- Schémas pour Stock ---
# Souvent, le stock est géré implicitement via les variantes ou des opérations dédiées.
# On définit un schéma de réponse si on doit l'exposer directement.

class StockBase(BaseModel):
    quantity: int = Field(..., ge=0)
    location: Optional[str] = Field(None, max_length=100)

class StockUpdate(BaseModel):
    # Pour mettre à jour directement une quantité
    quantity: int = Field(..., ge=0)
    location: Optional[str] = Field(None, max_length=100)

class StockResponse(StockBase):
    product_variant_id: int
    last_updated: datetime

    class Config:
        from_attributes = True

# --- Schémas pour ProductVariant ---

class ProductVariantBase(BaseModel):
    sku: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)
    attributes: Optional[Dict[str, Any]] = None
    image_url: Optional[HttpUrl] = None

class ProductVariantCreate(ProductVariantBase):
    product_id: int # Requis à la création
    initial_stock: Optional[int] = Field(0, ge=0, description="Stock initial lors de la création de la variante")

class ProductVariantUpdate(ProductVariantBase):
    # Permet de mettre à jour tous les champs de Base (sauf product_id)
    pass

class ProductVariantResponse(ProductVariantBase):
    id: int
    product_id: int
    stock: Optional[StockResponse] = None # Inclure l'info stock dans la réponse

    class Config:
        from_attributes = True

# --- Schémas pour Product (Principal) ---

class ProductBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    category_id: int
    is_active: bool = True
    image_url: Optional[HttpUrl] = None

class ProductCreate(ProductBase):
    tag_ids: Optional[List[int]] = [] # Liste d'IDs de tags existants à associer
    # Les variantes sont créées séparément

class ProductUpdate(ProductBase):
    # Permet de mettre à jour tous les champs de Base
    tag_ids: Optional[List[int]] = None # Permet de remplacer la liste des tags associés

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryResponse] = None
    tags: List[TagResponse] = []
    variants: List[ProductVariantResponse] = [] # Inclure les variantes dans la réponse produit

    class Config:
        from_attributes = True

# Pour les listes paginées
class PaginatedProductResponse(BaseModel):
    items: List[ProductResponse]
    total: int

class PaginatedCategoryResponse(BaseModel):
    items: List[CategoryResponse]
    total: int

class PaginatedTagResponse(BaseModel):
    items: List[TagResponse]
    total: int

class PaginatedVariantResponse(BaseModel):
    items: List[ProductVariantResponse]
    total: int 