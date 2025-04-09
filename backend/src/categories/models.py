from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from pydantic import ConfigDict

# Forward references pour les relations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..models.product import Product

# --- Modèle de base pour les catégories ---
class CategoryBase(SQLModel):
    """Modèle de base pour les catégories."""
    name: str = Field(index=True, unique=True, max_length=100)
    description: Optional[str] = Field(default=None)

# --- Modèle Category (Table) ---
# Ce fichier définit uniquement le modèle de table pour SQLAlchemy/SQLModel.
# Les schémas API (Create, Read, Update) sont dans category_api_schemas.py

class Category(CategoryBase, table=True):
    """Modèle de table pour les catégories."""
    id: Optional[int] = Field(default=None, primary_key=True)
    parent_category_id: Optional[int] = Field(default=None, foreign_key="categories.id", index=True)
    
    # Timestamps gérés par la DB (cf. table.sql)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    # Relations SQLModel
    parent: Optional["Category"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Category.id"}
    )
    children: List["Category"] = Relationship(back_populates="parent")
    products: List["Product"] = Relationship(back_populates="category")

    # Nom de la table
    __tablename__ = "categories"

    # Config pour permettre la lecture via .from_orm() ou FastAPI
    model_config = ConfigDict(from_attributes=True)

# -----------------------------------------------------------
# Rappel: Les Schémas API (Create, Read, Update) sont
# définis dans src/categories/interfaces/category_api_schemas.py
# et sont utilisés par les endpoints FastAPI et le service.
# -----------------------------------------------------------

# --- Schémas API ---
class CategoryCreate(CategoryBase):
    """Schéma pour la création d'une catégorie."""
    pass

class CategoryRead(CategoryBase):
    """Schéma pour la lecture d'une catégorie."""
    id: int
    parent_category_id: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class CategoryReadWithDetails(CategoryRead):
    """Schéma pour la lecture d'une catégorie avec ses relations."""
    children: List["CategoryRead"] = []
    products: List["Product"] = []

class CategoryUpdate(SQLModel):
    """Schéma pour la mise à jour d'une catégorie."""
    name: Optional[str] = None
    description: Optional[str] = None
    parent_category_id: Optional[int] = None

# --- Fin Modèle Category SQLModel --- 