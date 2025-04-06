from pydantic import Field, BaseModel
from typing import Optional, List
from datetime import datetime

# Import de la classe de base depuis le core
from src.core.schemas import OrmBaseModel

# ======================================================
# Schémas: Adresses
# ======================================================

class AddressBase(OrmBaseModel):
    street: str
    city: str
    zip_code: str
    country: str
    is_default: bool = False

class AddressCreate(AddressBase):
    # Ne contient pas user_id, car il sera fourni par le contexte (utilisateur connecté)
    pass

class AddressUpdate(BaseModel): # Pas besoin d'hériter d'OrmBaseModel car pas lu depuis DB
    street: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    # is_default n'est pas modifiable ici, géré par un endpoint dédié (/default)

class Address(AddressBase):
    id: int
    user_id: int
    # is_default est déjà dans AddressBase
    created_at: datetime
    updated_at: datetime 