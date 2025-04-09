"""
Implémentation des repositories pour les adresses.

Ce fichier contient les implémentations concrètes des repositories
utilisés dans le module addresses.
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from fastcrud import FastCRUD

from src.addresses.models import Address, AddressCreate, AddressRead, AddressUpdate, AddressList
from src.addresses.interfaces.repositories import AbstractAddressRepository
from src.addresses.exceptions import AddressNotFoundException, DuplicateAddressException

logger = logging.getLogger(__name__)

# Initialisation de FastCRUD pour le modèle Address
crud_address = FastCRUD[Address, AddressCreate, AddressUpdate](Address)

class SQLAlchemyAddressRepository(AbstractAddressRepository):
    """Implémentation SQLAlchemy du repository d'adresses."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, address_id: int) -> Optional[Address]:
        """Récupère une adresse par son ID."""
        return await crud_address.get(db=self.session, id=address_id)

    async def get_by_user_id(self, user_id: int, skip: int = 0, limit: int = 1000) -> AddressList:
        """Liste les adresses pour un utilisateur donné avec pagination et retourne le total."""
        # Récupérer le nombre total d'adresses
        count_query = select(func.count()).select_from(Address).where(Address.user_id == user_id)
        total = await self.session.scalar(count_query) or 0
        
        # Récupérer les adresses
        result = await crud_address.get_multi(
            db=self.session,
            offset=skip,
            limit=limit,
            filters={"user_id": user_id},
            sort_columns=["is_default", "id"],
            sort_orders=["desc", "asc"]
        )
        
        addresses = result.get('data', [])
        return AddressList(
            items=[AddressRead.model_validate(addr) for addr in addresses],
            total=total
        )

    async def create(self, address_data: Dict[str, Any]) -> Address:
        """Crée une nouvelle adresse."""
        try:
            return await crud_address.create(db=self.session, object=address_data)
        except Exception as e:
            logger.error(f"Erreur création adresse: {e}", exc_info=True)
            if "unique constraint" in str(e).lower():
                raise DuplicateAddressException(address_data.get("name", "unknown"))
            raise

    async def update(self, address_id: int, address_data: Dict[str, Any]) -> Optional[Address]:
        """Met à jour une adresse existante."""
        address = await self.get_by_id(address_id)
        if not address:
            logger.warning(f"Tentative MAJ adresse ID {address_id} non trouvée.")
            return None
        
        try:
            return await crud_address.update(
                db=self.session, 
                object=address_data, 
                id=address_id
            )
        except Exception as e:
            logger.error(f"Erreur MAJ adresse {address_id}: {e}", exc_info=True)
            if "unique constraint" in str(e).lower():
                raise DuplicateAddressException(address_data.get("name", "unknown"))
            raise

    async def delete(self, address_id: int) -> Optional[Address]:
        """Supprime une adresse."""
        address = await self.get_by_id(address_id)
        if not address:
            logger.warning(f"Tentative suppression adresse ID {address_id} non trouvée.")
            return None
        
        try:
            return await crud_address.delete(db=self.session, id=address_id)
        except Exception as e:
            logger.error(f"Erreur suppression adresse {address_id}: {e}", exc_info=True)
            raise

    async def set_default(self, address_id: int, user_id: int) -> None:
        """Définit une adresse comme étant l'adresse par défaut."""
        # Retirer le statut par défaut pour toutes les adresses de l'utilisateur
        query = update(Address).where(
            Address.user_id == user_id,
            Address.is_default == True
        ).values(is_default=False)
        await self.session.execute(query)
        
        # Définir la nouvelle adresse par défaut
        query = update(Address).where(Address.id == address_id).values(is_default=True)
        await self.session.execute(query)
        await self.session.commit()