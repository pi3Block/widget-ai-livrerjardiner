import logging
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session

# Domain
from src.orders.domain.repositories import AbstractOrderRepository
from src.products.domain.repositories import AbstractProductVariantRepository
from src.products.domain.repositories import AbstractStockRepository
from src.addresses.domain.repositories import AbstractAddressRepository

# Infrastructure
from src.orders.infrastructure.persistence import SQLAlchemyOrderRepository
from src.products.infrastructure.persistence import SQLAlchemyProductVariantRepository, SQLAlchemyStockRepository
from src.addresses.infrastructure.address_sql_repository import AddressSQLRepository

# Application
from src.orders.application.services import OrderService
from src.email.interfaces.dependencies import EmailServiceDep

# --- Repository Dependencies ---

def get_order_repository(
    session: AsyncSession = Depends(get_db_session)
) -> AbstractOrderRepository:
    """Fournit une instance de SQLAlchemyOrderRepository."""
    return SQLAlchemyOrderRepository(session=session)

# Note: Ces dépendances pour Variant, Stock et Address pourraient être centralisées
# si elles sont utilisées par plusieurs domaines, mais pour l'instant,
# nous les gardons ici pour la clarté de la dépendance de OrderService.
def get_variant_repository(
    session: AsyncSession = Depends(get_db_session)
) -> AbstractProductVariantRepository:
     """Fournit une instance de SQLAlchemyProductVariantRepository."""
     return SQLAlchemyProductVariantRepository(session=session)

def get_stock_repository(
    session: AsyncSession = Depends(get_db_session)
) -> AbstractStockRepository:
    """Fournit une instance de SQLAlchemyStockRepository."""
    return SQLAlchemyStockRepository(session=session)

def get_address_repository(
    session: AsyncSession = Depends(get_db_session)
) -> AbstractAddressRepository:
    """Fournit une instance de AddressSQLRepository."""
    return AddressSQLRepository(session=session)

# --- Service Dependencies ---

OrderRepositoryDep = Annotated[AbstractOrderRepository, Depends(get_order_repository)]
VariantRepositoryDep = Annotated[AbstractProductVariantRepository, Depends(get_variant_repository)]
StockRepositoryDep = Annotated[AbstractStockRepository, Depends(get_stock_repository)]
AddressRepositoryDep = Annotated[AbstractAddressRepository, Depends(get_address_repository)]

def get_order_service(
    order_repo: OrderRepositoryDep,
    variant_repo: VariantRepositoryDep,
    stock_repo: StockRepositoryDep,
    address_repo: AddressRepositoryDep,
    email_service: EmailServiceDep
) -> OrderService:
    """Injecte les repositories nécessaires et EmailService, et fournit une instance de OrderService."""
    return OrderService(
        order_repo=order_repo,
        variant_repo=variant_repo,
        stock_repo=stock_repo,
        address_repo=address_repo,
        email_service=email_service
    )

OrderServiceDep = Annotated[OrderService, Depends(get_order_service)] 