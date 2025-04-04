from pydantic import BaseModel, EmailStr, Field, Json
from typing import Optional, List, Any, Dict
from datetime import datetime
from decimal import Decimal # Pour les prix

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

class Address(AddressBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

class UserBase(OrmBaseModel):
    email: EmailStr
    name: Optional[str] = None

class UserCreate(UserBase):
    password: str # Mot de passe en clair lors de la création/login

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    addresses: List[Address] = [] # Relation chargée via ORM

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
    delivery_address: Optional[Address] = None # Relation chargée
    billing_address: Optional[Address] = None # Relation chargée
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
