from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Importations nécessaires (chemins à vérifier/adapter)
from src.core.database import get_db_session # Supposé exister
from src.addresses.domain.repositories import AbstractAddressRepository
from src.addresses.infrastructure.address_sql_repository import AddressSQLRepository
from src.addresses.application.services import AddressService

# Dépendance pour obtenir le dépôt d'adresses
def get_address_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> AbstractAddressRepository:
    """Injecte l'implémentation SQL du dépôt d'adresses."""
    return AddressSQLRepository(session=session)

# Dépendance pour obtenir le service d'adresses
def get_address_service(
    address_repo: Annotated[AbstractAddressRepository, Depends(get_address_repository)]
) -> AddressService:
    """Injecte le service d'adresses."""
    return AddressService(address_repo=address_repo) 