# backend/schemas.py
# Ce fichier contient les schémas Pydantic pour la validation des données API.
# Ces schémas sont distincts des modèles SQLAlchemy (définis dans models.py)
# mais peuvent être utilisés pour valider les données provenant de ces modèles grâce à from_attributes=True.

from pydantic import BaseModel, EmailStr, Field, Json, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime
from decimal import Decimal # Pour les prix

# ======================================================
# Configuration Commune Pydantic
# ======================================================

# Configuration commune pour activer le mode ORM (from_attributes)
class OrmBaseModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True # Remplace orm_mode
    )

# ======================================================
# Schémas: Utilisateurs & Adresses
# ======================================================

class AddressBase(OrmBaseModel):
    street: str
    city: str
    zip_code: str
    country: str
    is_default: bool = False

class AddressCreate(AddressBase):
    pass

class AddressUpdate(BaseModel): # Pas besoin d'hériter d'OrmBaseModel car pas lu depuis DB
    street: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

class Address(AddressBase):
    id: int
    user_id: int
    # is_default est déjà dans AddressBase
    created_at: datetime
    updated_at: datetime

class UserBase(OrmBaseModel):
    email: EmailStr
    name: Optional[str] = None

class UserCreate(UserBase):
    password: str # Mot de passe en clair lors de la création

class UserUpdate(BaseModel): # Pas besoin d'hériter d'OrmBaseModel
    name: Optional[str] = None
    # Pas de modif email/password/is_admin ici

class User(UserBase):
    id: int
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    addresses: List[Address] = [] # Relation chargée via ORM

# ======================================================
# Schémas: Catégories & Tags
# ======================================================

class CategoryBase(OrmBaseModel):
    name: str
    description: Optional[str] = None
    parent_category_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel): # Pas besoin d'hériter d'OrmBaseModel
    name: Optional[str] = None
    description: Optional[str] = None
    parent_category_id: Optional[int] = None

class Category(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # sub_categories: List['Category'] = [] # Peut être ajouté si nécessaire

class TagBase(OrmBaseModel):
    name: str

class TagCreate(TagBase):
    pass

class Tag(TagBase):
    id: int

# ======================================================
# Schémas: Produits & Variations
# ======================================================

# D'abord les variations car elles sont utilisées dans Product
class ProductVariantBase(OrmBaseModel):
    sku: str
    attributes: Optional[Dict[str, Any]] = None
    price: Decimal
    image_url: Optional[str] = None
    product_id: int # Ajouté car nécessaire pour la création/lecture

class ProductVariantCreate(ProductVariantBase):
    # Champs spécifiques à la création si nécessaire
    initial_stock: Optional[int] = 0 # Option pour créer le stock initial
    tag_names: Optional[List[str]] = None # Option pour lier/créer des tags
    pass

class ProductVariantUpdate(BaseModel): # Pas besoin d'hériter d'OrmBaseModel
    sku: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    price: Optional[Decimal] = None
    image_url: Optional[str] = None
    # product_id ne doit pas être modifié ici
    tag_names: Optional[List[str]] = None # Option pour remplacer les tags

class ProductVariant(ProductVariantBase):
    id: int
    created_at: datetime
    updated_at: datetime
    tags: List[Tag] = [] # Relation chargée
    # stock: Optional['Stock'] = None # Si on veut inclure le stock

# Maintenant le produit qui utilise ProductVariant
class ProductBase(OrmBaseModel):
    name: str
    base_description: Optional[str] = None
    category_id: Optional[int] = None

class ProductCreate(ProductBase):
    # Peut-être ajouter une liste de variants à créer en même temps ?
    # variants: List[ProductVariantCreate] = []
    pass

class ProductUpdate(BaseModel): # Pas besoin d'hériter d'OrmBaseModel
    name: Optional[str] = None
    base_description: Optional[str] = None
    category_id: Optional[int] = None

class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    variants: List[ProductVariant] = [] # Relation chargée
    category: Optional[Category] = None # Relation chargée

# ======================================================
# Schémas: Stock & Mouvements
# ======================================================

class StockBase(OrmBaseModel):
    product_variant_id: int
    quantity: int

class StockUpdate(BaseModel): # Pas besoin d'hériter d'OrmBaseModel
    # Typiquement, le stock est mis à jour par des mouvements, pas directement
    # Mais on pourrait avoir un endpoint admin pour ajuster la quantité
    quantity: Optional[int] = None

class Stock(StockBase):
    last_updated: datetime

class StockMovementBase(OrmBaseModel):
    product_variant_id: int
    quantity_change: int
    movement_type: str # Ex: 'sale', 'restock', 'adjustment', 'return'
    related_order_id: Optional[int] = None
    notes: Optional[str] = None
    # Ajout order_item_id si nécessaire
    order_item_id: Optional[int] = None 

class StockMovementCreate(StockMovementBase):
    pass

class StockMovement(StockMovementBase):
    id: int
    movement_date: datetime

# ======================================================
# Schémas: Devis (Quotes) & Lignes de Devis
# ======================================================

class QuoteItemBase(OrmBaseModel):
    product_variant_id: int
    quantity: int
    unit_price: Decimal # Prix au moment du devis

class QuoteItemCreate(QuoteItemBase):
    pass

class QuoteItem(QuoteItemBase):
    id: int
    quote_id: int
    variant: Optional[ProductVariant] = None # Peut être chargé

class QuoteBase(OrmBaseModel):
    user_id: int
    status: str = Field(default='pending', description="Ex: pending, accepted, rejected, expired")
    notes: Optional[str] = None

class QuoteCreate(QuoteBase):
    items: List[QuoteItemCreate] = []

class Quote(QuoteBase):
    id: int
    created_at: datetime
    updated_at: datetime
    valid_until: Optional[datetime] = None
    total_price: Optional[Decimal] = None # Calculé ou stocké
    items: List[QuoteItem] = [] # Relation chargée
    user: Optional[User] = None # Relation chargée

# Ajout du schéma QuoteUpdate manquant
class QuoteUpdate(BaseModel): # Pas besoin d'hériter d'OrmBaseModel
    status: Optional[str] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    # total_price est généralement calculé, pas mis à jour directement
    # Les items sont généralement gérés via des endpoints dédiés (ajout/suppression/modification)

# ======================================================
# Schémas: Commandes (Orders) & Lignes de Commande
# ======================================================

class OrderItemBase(OrmBaseModel):
    product_variant_id: int
    quantity: int
    unit_price: Decimal # Prix au moment de la commande

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: int
    order_id: int
    variant: Optional[ProductVariant] = None # Peut être chargé

class OrderBase(OrmBaseModel):
    user_id: int
    status: str = Field(default='pending', description="Ex: pending, processing, shipped, delivered, cancelled, returned")
    delivery_address_id: int
    billing_address_id: int
    shipping_method: Optional[str] = None
    shipping_cost: Decimal = Field(default=0.0)
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    items: List[OrderItemCreate] = []

class OrderUpdate(BaseModel): # Pas besoin d'hériter d'OrmBaseModel
    status: Optional[str] = None
    delivery_address_id: Optional[int] = None
    billing_address_id: Optional[int] = None
    shipping_method: Optional[str] = None
    shipping_cost: Optional[Decimal] = None
    notes: Optional[str] = None
    # La modification des items est généralement plus complexe

class Order(OrderBase):
    id: int
    order_date: datetime
    updated_at: datetime
    total_price: Optional[Decimal] = None # Calculé ou stocké
    items: List[OrderItem] = [] # Relation chargée
    user: Optional[User] = None # Relation chargée
    delivery_address: Optional[Address] = None # Relation chargée
    billing_address: Optional[Address] = None # Relation chargée

# --- Autres Schémas ---

# Exemple pour l'authentification (déjà défini dans auth.py, mais peut être centralisé ici)
# class Token(BaseModel):
#     access_token: str
#     token_type: str

# class TokenData(BaseModel):
#     user_id: Optional[int] = None 