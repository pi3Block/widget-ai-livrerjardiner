from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import ConfigDict

# --- Modèles pour QuoteItem ---

class QuoteItemBase(SQLModel):
    """Modèle de base pour un item de devis (données communes)."""
    product_variant_id: int = Field(foreign_key="product_variants.id", index=True)
    quantity: int = Field(..., gt=0)
    # Le prix unitaire sera défini dans les schémas spécifiques (Create/Read)
    
    model_config = ConfigDict(from_attributes=True)

class QuoteItem(QuoteItemBase, table=True):
    """Modèle de table pour un item de devis."""
    id: Optional[int] = Field(default=None, primary_key=True)
    quote_id: int = Field(foreign_key="quotes.id", index=True)
    unit_price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    __tablename__ = "quote_items"

class QuoteItemCreate(SQLModel):
    """Schéma pour créer un item de devis (potentiellement avec prix fourni ou validé)."""
    product_variant_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)

class QuoteItemRead(QuoteItemBase):
    """Schéma pour lire un item de devis depuis l'API."""
    id: int
    quote_id: int
    unit_price: Decimal = Field(..., max_digits=10, decimal_places=2)
    # product_variant: Optional[ProductVariantRead] = None # Potentiellement charger la variante

# --- Modèles pour Quote ---

class QuoteBase(SQLModel):
    """Modèle de base pour un devis."""
    user_id: int = Field(foreign_key="users.id", index=True)
    status: str = Field(..., max_length=50) # Le statut est souvent requis
    # total_price est calculé et ajouté dans QuoteRead

    model_config = ConfigDict(from_attributes=True)

class Quote(QuoteBase, table=True):
    """Modèle de table pour un devis."""
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relations
    items: List["QuoteItem"] = []

    __tablename__ = "quotes"

class QuoteCreate(SQLModel): # Ne pas hériter de Base pour contrôler les champs de création
    """Schéma pour créer un nouveau devis via l'API."""
    user_id: int # Requis explicitement à la création (même si vérifié contre l'utilisateur courant)
    items: List[QuoteItemCreate]

class QuoteRead(QuoteBase):
    """Schéma pour lire un devis depuis l'API."""
    id: int
    created_at: datetime
    updated_at: datetime
    total_price: Optional[Decimal] = Field(None, description="Prix total calculé", ge=0, max_digits=12, decimal_places=2)
    items: List[QuoteItemRead] = []
    # user: Optional[UserRead] = None # Potentiellement charger l'utilisateur

class QuoteUpdate(SQLModel): # Modèle spécifique pour la mise à jour (souvent juste le statut)
    """Schéma pour mettre à jour le statut d'un devis."""
    status: str = Field(..., max_length=50)

class PaginatedQuoteRead(SQLModel):
    """Schéma pour une réponse paginée de devis."""
    items: List[QuoteRead]
    total: int 