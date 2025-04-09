from fastcrud import FastCRUD
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.sql import func
from typing import List, Optional, Dict, Any, Type, Tuple
# Import SQLModel for DeleteSchemaType and AddressRead for SelectSchemaType
from sqlmodel import SQLModel
from src.addresses.models import Address, AddressCreate, AddressRead, AddressUpdate, AddressList

# Initialisation de FastCRUD pour le modèle Address avec les 6 types
# Utiliser AddressUpdate pour UpdateInternal et SQLModel pour Delete
crud_address = FastCRUD[Address, AddressCreate, AddressUpdate, AddressUpdate, SQLModel, AddressRead](Address)

# === Fonctions CRUD ===
async def get_address(
    db: AsyncSession, 
    address_id: int,
    schema_to_select: Optional[Type[AddressRead]] = None
) -> Optional[Address]:
    """
    Récupère une adresse par son identifiant.
    
    Args:
        db: Session de base de données
        address_id: Identifiant de l'adresse
        schema_to_select: Schéma à utiliser pour la sélection (optionnel)
        
    Returns:
        Optional[Address]: L'adresse trouvée ou None
    """
    return await crud_address.get(db=db, id=address_id, schema_to_select=schema_to_select)

async def get_user_addresses(
    db: AsyncSession, 
    user_id: int,
    skip: int = 0,
    limit: int = 1000 
) -> Tuple[List[Address], int]:
    """
    Récupère toutes les adresses d'un utilisateur.
    
    Args:
        db: Session de base de données
        user_id: Identifiant de l'utilisateur
        skip: Nombre d'adresses à sauter (pagination)
        limit: Nombre maximum d'adresses à récupérer
        
    Returns:
        Tuple[List[Address], int]: Liste des adresses et nombre total
    """
    # Récupérer le nombre total d'adresses
    count_query = select(func.count()).select_from(Address).where(Address.user_id == user_id)
    total = await db.scalar(count_query) or 0
    
    # Récupérer les adresses
    result = await crud_address.get_multi(
        db=db,
        offset=skip,
        limit=limit,
        filters={"user_id": user_id},
        sort_columns=["is_default", "id"],
        sort_orders=["desc", "asc"]
    )
    
    return result.get('data', []), total

async def create_address(
    db: AsyncSession, 
    address_data: Dict[str, Any]
) -> Address:
    """
    Crée une nouvelle adresse dans la base de données.
    
    Args:
        db: Session de base de données
        address_data: Données de l'adresse à créer
        
    Returns:
        Address: L'adresse créée
    """
    return await crud_address.create(db=db, object=address_data)

async def update_address(
    db: AsyncSession, 
    address_id: int, 
    address_update_data: AddressUpdate | Dict[str, Any],
) -> Optional[Address]:
    """
    Met à jour une adresse existante.
    
    Args:
        db: Session de base de données
        address_id: Identifiant de l'adresse à mettre à jour
        address_update_data: Données de mise à jour
        
    Returns:
        Optional[Address]: L'adresse mise à jour ou None
    """
    return await crud_address.update(
        db=db, 
        object=address_update_data, 
        id=address_id,
    )

async def delete_address(db: AsyncSession, address_id: int) -> Optional[Address]:
    """
    Supprime une adresse de la base de données.
    
    Args:
        db: Session de base de données
        address_id: Identifiant de l'adresse à supprimer
        
    Returns:
        Optional[Address]: L'adresse supprimée ou None
    """
    return await crud_address.delete(db=db, id=address_id)

async def unset_default_address(db: AsyncSession, user_id: int) -> None:
    """
    Retire le statut d'adresse par défaut pour toutes les adresses d'un utilisateur.
    
    Args:
        db: Session de base de données
        user_id: Identifiant de l'utilisateur
    """
    # Utiliser une requête SQL directe pour plus d'efficacité
    query = update(Address).where(
        Address.user_id == user_id,
        Address.is_default == True
    ).values(is_default=False)
    await db.execute(query)
    await db.commit()

async def set_address_as_default(db: AsyncSession, address_id: int) -> None:
    """
    Définit une adresse comme étant l'adresse par défaut.
    
    Args:
        db: Session de base de données
        address_id: Identifiant de l'adresse à définir par défaut
    """
    # Utiliser une requête SQL directe pour plus d'efficacité
    query = update(Address).where(Address.id == address_id).values(is_default=True)
    await db.execute(query)
    await db.commit()

# === Repository SQL ===
class AddressSQLRepository:
    """
    Repository pour les opérations SQL sur les adresses.
    
    Ce repository encapsule les opérations CRUD de base et fournit
    une interface cohérente pour le service.
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
        return await get_address(self.db, address_id)

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
        addresses, total = await get_user_addresses(self.db, user_id, skip, limit)
        return AddressList(
            items=[AddressRead.model_validate(addr) for addr in addresses],
            total=total
        )

    async def create(self, address_data: Dict[str, Any]) -> Address:
        """
        Crée une nouvelle adresse.
        
        Args:
            address_data: Données de l'adresse à créer
            
        Returns:
            Address: L'adresse créée
        """
        return await create_address(self.db, address_data)

    async def update(self, address_id: int, address_data: Dict[str, Any]) -> Optional[Address]:
        """
        Met à jour une adresse existante.
        
        Args:
            address_id: Identifiant de l'adresse à mettre à jour
            address_data: Données de mise à jour
            
        Returns:
            Optional[Address]: L'adresse mise à jour ou None
        """
        return await update_address(self.db, address_id, address_data)

    async def delete(self, address_id: int) -> Optional[Address]:
        """
        Supprime une adresse.
        
        Args:
            address_id: Identifiant de l'adresse à supprimer
            
        Returns:
            Optional[Address]: L'adresse supprimée ou None
        """
        return await delete_address(self.db, address_id)

    async def set_default(self, address_id: int, user_id: int) -> None:
        """
        Définit une adresse comme étant l'adresse par défaut.
        
        Args:
            address_id: Identifiant de l'adresse à définir par défaut
            user_id: Identifiant de l'utilisateur
        """
        await unset_default_address(self.db, user_id)
        await set_address_as_default(self.db, address_id) 