"""
Modèles pour le module PDF.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal
from sqlmodel import SQLModel, Field, Relationship

class PDFRequestBase(SQLModel):
    """
    Modèle de base pour une requête PDF.
    """
    template_name: str = Field(..., description="Nom du template à utiliser")
    data: Dict[str, Any] = Field(..., description="Données à injecter dans le template")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Options de génération du PDF")

class PDFRequest(PDFRequestBase, table=True):
    """
    Modèle de table pour une requête PDF.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="ID de l'utilisateur qui a fait la requête")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Date de création")
    status: str = Field(..., description="Statut de la requête")
    file_path: Optional[str] = Field(default=None, description="Chemin du fichier PDF généré")
    error: Optional[str] = Field(default=None, description="Message d'erreur si la génération a échoué")
    processing_time: Optional[float] = Field(default=None, description="Temps de traitement en secondes")

class PDFRequestCreate(PDFRequestBase):
    """
    Schéma pour la création d'une requête PDF.
    """
    pass

class PDFRequestRead(PDFRequestBase):
    """
    Schéma pour la lecture d'une requête PDF.
    """
    id: int
    user_id: Optional[int]
    created_at: datetime
    status: str
    file_path: Optional[str]
    processing_time: Optional[float]

class PDFRequestUpdate(SQLModel):
    """
    Schéma pour la mise à jour d'une requête PDF.
    """
    template_name: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    file_path: Optional[str] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

class PDFQuoteUserBase(SQLModel):
    """
    Modèle de base pour les informations utilisateur dans un devis PDF.
    """
    name: str = Field(default="Client Inconnu", description="Nom du client")
    email: Optional[str] = Field(default=None, description="Email du client")

class PDFQuoteItemVariantBase(SQLModel):
    """
    Modèle de base pour les détails d'une variante de produit.
    """
    name: str = Field(default="Article Inconnu", description="Nom de la variante")

class PDFQuoteItemBase(SQLModel):
    """
    Modèle de base pour un article dans un devis PDF.
    """
    variant_sku: str = Field(default="N/A", description="Référence SKU de la variante")
    quantity: int = Field(default=0, description="Quantité de l'article")
    price_at_quote: Decimal = Field(default=0.0, description="Prix unitaire au moment du devis")

class PDFQuoteDataBase(SQLModel):
    """
    Modèle de base pour les données d'un devis PDF.
    """
    id: str = Field(default="N/A", description="Identifiant unique du devis")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Date de création du devis")
    total_amount: Decimal = Field(default=0.0, description="Montant total du devis")

class PDFQuoteData(PDFQuoteDataBase, table=True):
    """
    Modèle de table pour les données d'un devis PDF.
    """
    user: PDFQuoteUserBase = Field(default_factory=PDFQuoteUserBase)
    items: List[PDFQuoteItemBase] = Field(default_factory=list)

class PDFQuoteDataCreate(PDFQuoteDataBase):
    """
    Schéma pour la création d'un devis PDF.
    """
    user: PDFQuoteUserBase
    items: List[PDFQuoteItemBase]

class PDFQuoteDataRead(PDFQuoteDataBase):
    """
    Schéma pour la lecture d'un devis PDF.
    """
    user: PDFQuoteUserBase
    items: List[PDFQuoteItemBase] 