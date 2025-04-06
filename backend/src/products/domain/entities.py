from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl

# Entités du Domaine "Products"
# Basées sur les modèles SQLAlchemy mais définies ici pour le découplage.
# On utilise Pydantic pour la validation et la structure.

class Tag(BaseModel):
    id: int
    name: str = Field(..., max_length=50)
    description: Optional[str] = None

    class Config:
        from_attributes = True # Permet de charger depuis les attributs de l'objet SQLAlchemy

class Category(BaseModel):
    id: int
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    parent_id: Optional[int] = None # Pour les sous-catégories

    class Config:
        from_attributes = True

class Stock(BaseModel):
    # Représente le niveau de stock pour UNE variante spécifique
    product_variant_id: int 
    quantity: int = Field(..., ge=0)
    location: Optional[str] = Field(None, max_length=100) # Ex: 'Entrepôt A', 'Magasin B'
    last_updated: datetime

    class Config:
        from_attributes = True

class ProductVariant(BaseModel):
    id: int
    product_id: int
    sku: str = Field(..., max_length=100, description="Stock Keeping Unit unique")
    name: str = Field(..., max_length=255, description="Nom spécifique de la variante, ex: 'T-Shirt Rouge - Taille L'")
    price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)
    attributes: Optional[dict] = None # Ex: {"couleur": "Rouge", "taille": "L"}
    image_url: Optional[str] = None
    # stock: Optional[Stock] = None # Le stock est géré séparément via repo dédié

    class Config:
        from_attributes = True

class Product(BaseModel):
    id: int
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    slug: str = Field(..., index=True, description="URL-friendly name")
    category_id: int
    image_url: Optional[HttpUrl] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    category: Optional[Category] = None # Relation chargée optionnellement
    tags: List[Tag] = []              # Relation chargée optionnellement
    variants: List[ProductVariant] = [] # Relation chargée optionnellement

    class Config:
        from_attributes = True 