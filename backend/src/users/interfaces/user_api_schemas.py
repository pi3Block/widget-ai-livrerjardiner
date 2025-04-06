from pydantic import EmailStr, Field
from typing import Optional, List
from datetime import datetime

# Import de la classe de base depuis le core
from src.core.schemas import OrmBaseModel
# Import BaseModel directement, car il n'est pas dans OrmBaseModel pour Update
from pydantic import BaseModel

# ======================================================
# Schémas: Adresses (SUPPRIMÉS - déplacés vers addresses/interface)
# ======================================================

# class AddressBase(OrmBaseModel): # Supprimé
# class AddressCreate(AddressBase): # Supprimé
# class AddressUpdate(BaseModel): # Supprimé
# class Address(AddressBase): # Supprimé

# ======================================================
# Schémas: Utilisateurs
# ======================================================

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
    # Le champ addresses est retiré du schéma User API pour l'instant.
    # Il pourra être ajouté si un endpoint le nécessite spécifiquement,
    # en chargeant les adresses via le service Address.
    # addresses: List[schemas.Address] = [] # Temporairement retiré

# ======================================================
# Schémas: Authentification (Token)
# ======================================================

class TokenData(BaseModel): # Pas OrmBaseModel, juste structure de données
    user_id: Optional[int] = None

class Token(BaseModel): # Pas OrmBaseModel
    access_token: str
    token_type: str
