# src/users/models.py
"""
Module définissant les modèles SQLModel pour l'entité User.

Ce module contient :
- UserBase : Classe SQLModel de base avec les champs communs.
- User : Modèle de table SQLModel (table=True) héritant de UserBase.
- UserCreate, UserRead, UserUpdate : Schémas Pydantic/SQLModel pour l'API.
"""
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr

# Import pour gérer les relations si d'autres modules existent
# if TYPE_CHECKING:
#     from src.addresses.models import Address # Exemple
#     from src.orders.models import Order # Exemple
#     from src.quotes.models import Quote # Exemple

# =====================================================
# Schémas: Utilisateurs (SQLModel approach)
# =====================================================

class UserBase(SQLModel):
    """Modèle SQLModel de base pour un utilisateur (données communes, Pydantic)."""
    email: EmailStr = Field(unique=True, index=True, max_length=255, nullable=False)
    name: Optional[str] = Field(default=None, max_length=100)
    is_admin: bool = Field(default=False, nullable=False)
    # created_at et updated_at seront dans le modèle de table avec server_default

# ----- Modèle de Table -----
class User(UserBase, table=True):
    """Modèle de table SQLModel pour les utilisateurs."""
    __tablename__ = "users" # Facultatif si nom de classe = nom de table

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    password_hash: str = Field(nullable=False, max_length=255) # Renommé depuis hashed_password pour clarté

    # Utilisation de Field avec default=None et sa_column_kwargs pour server_default
    # Voir: https://sqlmodel.tiangolo.com/tutorial/column-types/#datetime-with-timezone
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={"server_default": "func.now()", "nullable": False}
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column_kwargs={"server_default": "func.now()", "onupdate": "func.now()", "nullable": False}
    )

    # --- Relations (Exemples, à adapter si les modules/modèles existent) ---
    # Utiliser Relationship de SQLModel
    # addresses: List["Address"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    # orders: List["Order"] = Relationship(back_populates="user")
    # quotes: List["Quote"] = Relationship(back_populates="user")

# ----- Schémas API -----
class UserCreate(UserBase):
    """Schéma Pydantic/SQLModel pour la création d'un utilisateur."""
    password: str # Mot de passe en clair lors de la création

class UserRead(UserBase):
    """Schéma Pydantic/SQLModel pour lire les données d'un utilisateur."""
    id: int
    created_at: datetime
    updated_at: datetime
    # Ajouter les relations ici si elles doivent être retournées par l'API
    # addresses: List["AddressRead"] = [] # Exemple

class UserUpdate(SQLModel): # Pas besoin d'hériter de UserBase si seuls certains champs sont maj
    """Schéma Pydantic/SQLModel pour la mise à jour partielle d'un utilisateur."""
    name: Optional[str] = None
    # Pas de modif email/password/is_admin ici par défaut
    # Si la modification de is_admin est permise, ajouter :
    # is_admin: Optional[bool] = None 