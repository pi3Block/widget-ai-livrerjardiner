from datetime import datetime
from typing import Optional, List, ForwardRef
import re
from sqlmodel import SQLModel, Field, Relationship, select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ConfigDict, field_validator, model_validator

# --- Modèle de base pour les adresses ---
class AddressBase(SQLModel):
    """
    Schéma de base pour les adresses, contenant les champs communs.
    
    Attributes:
        street: Nom de la rue
        city: Ville
        zip_code: Code postal
        country: Pays
        is_default: Indique si c'est l'adresse par défaut de l'utilisateur
    """
    street: str = Field(max_length=255, index=True)
    city: str = Field(max_length=100, index=True)
    zip_code: str = Field(max_length=20, index=True)
    country: str = Field(max_length=100, index=True)
    is_default: bool = Field(default=False, index=True)
    
    @field_validator('street')
    @classmethod
    def validate_street(cls, v):
        """
        Valide le nom de la rue.
        
        Args:
            v: Valeur du champ street
            
        Returns:
            str: La valeur validée
            
        Raises:
            ValueError: Si la rue est vide ou ne contient que des espaces
        """
        if not v or v.strip() == "":
            raise ValueError("Le nom de la rue ne peut pas être vide")
        return v.strip()
    
    @field_validator('city')
    @classmethod
    def validate_city(cls, v):
        """
        Valide le nom de la ville.
        
        Args:
            v: Valeur du champ city
            
        Returns:
            str: La valeur validée
            
        Raises:
            ValueError: Si la ville est vide ou ne contient que des espaces
        """
        if not v or v.strip() == "":
            raise ValueError("Le nom de la ville ne peut pas être vide")
        return v.strip()
    
    @field_validator('zip_code')
    @classmethod
    def validate_zip_code(cls, v):
        """
        Valide le code postal.
        
        Args:
            v: Valeur du champ zip_code
            
        Returns:
            str: La valeur validée
            
        Raises:
            ValueError: Si le code postal n'est pas au format valide
        """
        if not v or v.strip() == "":
            raise ValueError("Le code postal ne peut pas être vide")
        
        # Format français: 5 chiffres
        if not re.match(r'^\d{5}$', v.strip()):
            raise ValueError("Le code postal doit être au format français (5 chiffres)")
        
        return v.strip()
    
    @field_validator('country')
    @classmethod
    def validate_country(cls, v):
        """
        Valide le nom du pays.
        
        Args:
            v: Valeur du champ country
            
        Returns:
            str: La valeur validée
            
        Raises:
            ValueError: Si le pays est vide ou ne contient que des espaces
        """
        if not v or v.strip() == "":
            raise ValueError("Le nom du pays ne peut pas être vide")
        return v.strip()

# --- Modèle de table pour les adresses ---
class Address(AddressBase, table=True):
    """
    Modèle de domaine représentant une adresse.
    
    Attributes:
        id: Identifiant unique de l'adresse
        user_id: Identifiant de l'utilisateur propriétaire
        latitude: Latitude de l'adresse
        longitude: Longitude de l'adresse
        created_at: Date de création
        updated_at: Date de dernière mise à jour
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relation avec l'utilisateur (définie dans le modèle User)
    user: Optional["User"] = Relationship(back_populates="addresses")
    
    @model_validator(mode='after')
    def update_timestamp(self) -> 'Address':
        """
        Met à jour le timestamp updated_at à chaque modification.
        """
        self.updated_at = datetime.utcnow()
        return self

# --- Schémas API pour les adresses ---
class AddressCreate(AddressBase):
    """
    Schéma pour la création d'une adresse.
    
    Ce schéma est utilisé lors de la création d'une nouvelle adresse.
    L'ID utilisateur n'est pas inclus car il est fourni par le contexte d'authentification.
    """
    pass

class AddressRead(AddressBase):
    """
    Schéma pour la lecture d'une adresse.
    
    Ce schéma est utilisé pour retourner les données d'une adresse.
    Il inclut les champs supplémentaires comme l'ID et les timestamps.
    
    Attributes:
        id: Identifiant unique de l'adresse
        user_id: Identifiant de l'utilisateur propriétaire
        created_at: Date de création
        updated_at: Date de dernière mise à jour
    """
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AddressUpdate(SQLModel):
    """
    Schéma pour la mise à jour d'une adresse.
    
    Tous les champs sont optionnels car seule une partie de l'adresse peut être mise à jour.
    Le champ is_default n'est pas modifiable via ce schéma, il est géré par un endpoint dédié.
    
    Attributes:
        street: Nouveau nom de rue (optionnel)
        city: Nouvelle ville (optionnel)
        zip_code: Nouveau code postal (optionnel)
        country: Nouveau pays (optionnel)
    """
    street: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    zip_code: Optional[str] = Field(default=None, max_length=20)
    country: Optional[str] = Field(default=None, max_length=100)
    
    @field_validator('street')
    @classmethod
    def validate_street(cls, v):
        """
        Valide le nom de la rue (optionnel).
        
        Args:
            v: Valeur du champ street
            
        Returns:
            Optional[str]: La valeur validée ou None
            
        Raises:
            ValueError: Si la rue ne contient que des espaces
        """
        if v is not None and v.strip() == "":
            raise ValueError("Le nom de la rue ne peut pas être vide")
        return v.strip() if v is not None else None
    
    @field_validator('city')
    @classmethod
    def validate_city(cls, v):
        """
        Valide le nom de la ville (optionnel).
        
        Args:
            v: Valeur du champ city
            
        Returns:
            Optional[str]: La valeur validée ou None
            
        Raises:
            ValueError: Si la ville ne contient que des espaces
        """
        if v is not None and v.strip() == "":
            raise ValueError("Le nom de la ville ne peut pas être vide")
        return v.strip() if v is not None else None
    
    @field_validator('zip_code')
    @classmethod
    def validate_zip_code(cls, v):
        """
        Valide le code postal (optionnel).
        
        Args:
            v: Valeur du champ zip_code
            
        Returns:
            Optional[str]: La valeur validée ou None
            
        Raises:
            ValueError: Si le code postal n'est pas au format valide
        """
        if v is not None:
            if v.strip() == "":
                raise ValueError("Le code postal ne peut pas être vide")
            
            # Format français: 5 chiffres
            if not re.match(r'^\d{5}$', v.strip()):
                raise ValueError("Le code postal doit être au format français (5 chiffres)")
            
            return v.strip()
        return None
    
    @field_validator('country')
    @classmethod
    def validate_country(cls, v):
        """
        Valide le nom du pays (optionnel).
        
        Args:
            v: Valeur du champ country
            
        Returns:
            Optional[str]: La valeur validée ou None
            
        Raises:
            ValueError: Si le pays ne contient que des espaces
        """
        if v is not None and v.strip() == "":
            raise ValueError("Le nom du pays ne peut pas être vide")
        return v.strip() if v is not None else None

# --- Schéma pour la liste des adresses ---
class AddressList(SQLModel):
    """
    Schéma pour la liste des adresses d'un utilisateur.
    
    Attributes:
        items: Liste des adresses
        total: Nombre total d'adresses
    """
    items: List[AddressRead]
    total: int

# --- Repository pour les opérations CRUD ---
class AddressRepository:
    """
    Repository pour les opérations CRUD sur les adresses.
    
    Cette classe encapsule toutes les opérations de base de données
    liées aux adresses en utilisant SQLModel directement.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialise le repository avec une session de base de données.
        
        Args:
            db: Session de base de données
        """
        self.db = db

    async def get_by_id(self, address_id: int) -> Optional[Address]:
        """
        Récupère une adresse par son ID.
        
        Args:
            address_id: Identifiant de l'adresse
            
        Returns:
            Optional[Address]: L'adresse trouvée ou None
        """
        query = select(Address).where(Address.id == address_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int, skip: int = 0, limit: int = 1000) -> AddressList:
        """
        Récupère toutes les adresses d'un utilisateur.
        
        Args:
            user_id: Identifiant de l'utilisateur
            skip: Nombre d'adresses à sauter (pagination)
            limit: Nombre maximum d'adresses à récupérer
            
        Returns:
            AddressList: Liste des adresses et nombre total
        """
        # Récupérer le nombre total d'adresses
        count_query = select(func.count()).select_from(Address).where(Address.user_id == user_id)
        total = await self.db.scalar(count_query) or 0
        
        # Récupérer les adresses
        query = (
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.is_default.desc(), Address.id.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        addresses = result.scalars().all()
        
        return AddressList(
            items=[AddressRead.model_validate(addr) for addr in addresses],
            total=total
        )

    async def create(self, address_data: dict) -> Address:
        """
        Crée une nouvelle adresse.
        
        Args:
            address_data: Données de l'adresse à créer
            
        Returns:
            Address: L'adresse créée
        """
        address = Address(**address_data)
        self.db.add(address)
        await self.db.commit()
        await self.db.refresh(address)
        return address

    async def update(self, address_id: int, address_data: dict) -> Optional[Address]:
        """
        Met à jour une adresse existante.
        
        Args:
            address_id: Identifiant de l'adresse à mettre à jour
            address_data: Données de mise à jour
            
        Returns:
            Optional[Address]: L'adresse mise à jour ou None
        """
        address = await this.get_by_id(address_id)
        if not address:
            return None
            
        for key, value in address_data.items():
            setattr(address, key, value)
            
        await this.db.commit()
        await this.db.refresh(address)
        return address

    async def delete(self, address_id: int) -> Optional[Address]:
        """
        Supprime une adresse.
        
        Args:
            address_id: Identifiant de l'adresse à supprimer
            
        Returns:
            Optional[Address]: L'adresse supprimée ou None
        """
        address = await this.get_by_id(address_id)
        if not address:
            return None
            
        await this.db.delete(address)
        await this.db.commit()
        return address

    async def set_default(self, address_id: int, user_id: int) -> None:
        """
        Définit une adresse comme étant l'adresse par défaut.
        
        Args:
            address_id: Identifiant de l'adresse à définir par défaut
            user_id: Identifiant de l'utilisateur
        """
        # Retirer le statut par défaut de toutes les adresses de l'utilisateur
        query = (
            select(Address)
            .where(Address.user_id == user_id, Address.is_default == True)
        )
        result = await this.db.execute(query)
        default_addresses = result.scalars().all()
        
        for addr in default_addresses:
            addr.is_default = False
            
        # Définir la nouvelle adresse par défaut
        address = await this.get_by_id(address_id)
        if address and address.user_id == user_id:
            address.is_default = True
            
        await this.db.commit() 