from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

# Forward reference
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.product_variants.models import ProductVariant, ProductVariantTagLink # Ajuster l'import

# --- Modèle Tag SQLModel ---

class TagBase(SQLModel):
    name: str = Field(index=True, unique=True, max_length=50)

class Tag(TagBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # Relation Many-to-Many avec ProductVariant via le modèle de lien
    product_variants: List["ProductVariant"] = Relationship(back_populates="tags", link_model=ProductVariantTagLink)

    __tablename__ = "tags"

# Schémas API pour Tag
class TagCreate(TagBase):
    pass

class TagRead(TagBase):
    id: int

class TagUpdate(SQLModel):
    name: Optional[str] = None

# --- Fin Modèle Tag SQLModel --- 