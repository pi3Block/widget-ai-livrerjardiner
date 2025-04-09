import logging
from abc import ABC, abstractmethod
from typing import Annotated, Dict, List, Optional, Tuple, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastcrud import FastCRUD

# Importations nécessaires (chemins à vérifier/adapter)
from src.database import get_db_session # Chemin correcté pour être absolu depuis src
from src.orders.service import OrderService # Chemin corrigé pour être absolu depuis src

# Import des dépendances pour UserService
from src.users.service import UserService
from src.users.dependencies import get_user_service

# Models
from src.orders.models import Order, OrderItem

# Repository Implementation
from src.orders.persistence import SQLAlchemyOrderRepository

# Import des dépendances pour les autres services
from src.product_variants.repositories import SQLAlchemyProductVariantRepository
from src.stock.repositories import SQLAlchemyStockRepository
from src.addresses.repositories import AddressSQLRepository

# Import des interfaces abstraites
from src.product_variants.interfaces.repositories import AbstractProductVariantRepository
from src.stock.interfaces.repositories import AbstractStockRepository
from src.addresses.interfaces.repositories import AbstractAddressRepository

# Import des services dépendants
from src.addresses.service import AddressService
from src.email.services import EmailService
from src.product_variants.service import ProductVariantService
from src.stock.service import StockService

# Import des dépendances pour les services
from src.addresses.dependencies import get_address_service
from src.email.dependencies import get_email_service
from src.product_variants.dependencies import get_variant_service
from src.stock.dependencies import get_stock_service

# --- Nouveaux Imports --- 
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends # Ajouter Depends pour l'injection future
from typing import Annotated # Pour les annotations de dépendance

# --- Database Session Dependency --- 
from src.database import get_db_session
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]

# --- Service Dependencies (Existing - Keep them) --- 
# ... Garder les dépendances pour AddressService, EmailService, etc. ...
from src.addresses.dependencies import AddressServiceDep
from src.email.dependencies import EmailServiceDep
from src.products.dependencies import ProductVariantServiceDep
from src.stock.dependencies import StockServiceDep

# --- Repository Dependency (NEW) --- 
from src.orders.interfaces.repositories import AbstractOrderRepository
from src.orders.repositories import SQLAlchemyOrderRepository

def get_order_repository(session: SessionDep) -> AbstractOrderRepository:
    """Fournit une instance du repository de commandes."""
    logger.debug("Providing SQLAlchemyOrderRepository")
    return SQLAlchemyOrderRepository(db_session=session)

OrderRepositoryDep = Annotated[AbstractOrderRepository, Depends(get_order_repository)]

# --- Order Service Dependency (UPDATE) --- 
from src.orders.service import OrderService
# Importer les services dont OrderService dépend directement pour l'injection
from src.addresses.service import AddressService
from src.email.services import EmailService
from src.products.application.services import ProductVariantService
from src.stock.services import StockService


def get_order_service(
    # Injecter le nouveau repository
    order_repository: OrderRepositoryDep, 
    # Injecter les autres services via leurs dépendances existantes
    address_service: AddressServiceDep, 
    email_service: EmailServiceDep, 
    product_variant_service: ProductVariantServiceDep, 
    stock_service: StockServiceDep,
    # Retirer db: SessionDep si OrderService ne l'utilise plus directement
) -> OrderService:
    """
    Fournit une instance du service de gestion des commandes,
    injectant le repository et les autres services dépendants.
    """
    logger.debug("Providing OrderService with injected repository and other services")
    return OrderService(
        order_repository=order_repository,
        address_service=address_service,
        email_service=email_service,
        product_variant_service=product_variant_service,
        stock_service=stock_service
        # Ne pas passer db si le service n'en dépend plus
    )

OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]

# --- CRUD Dependencies (REMOVE - Logic moved to Repository) --- 
# Supprimer get_order_crud, get_order_item_crud et leurs dépendances annotées
# ...

# --- Specific Getters/Validators (KEEP/ADAPT) --- 
# Examiner si get_order_for_update et get_validated_order_item 
# sont toujours nécessaires ou si leur logique est intégrée 
# au service/repository. Si elles restent, les adapter pour utiliser 
# OrderServiceDep ou OrderRepositoryDep si applicable.

# Exemple d'adaptation (si get_order_for_update reste une dépendance distincte):
# async def get_order_for_update(
#     order_id: int,
#     order_repo: OrderRepositoryDep # Utiliser le repo
# ) -> Order:
#     order = await order_repo.get_by_id(order_id)
#     if not order:
#         raise OrderNotFoundHTTPException(order_id)
#     # ... autre logique ...
#     return order

# Supprimer les dépendances CRUD non utilisées
# OrderCrudDep = Annotated[FastCRUD, Depends(get_order_crud)]
# OrderItemCrudDep = Annotated[FastCRUD, Depends(get_order_item_crud)]

# Mettre à jour les dépendances spécifiques si elles sont conservées
# ValidatedOrderDep = Annotated[Order, Depends(get_order_for_update)]
# ValidatedItemDep = Annotated[OrderItem, Depends(get_validated_order_item)]
# ... existing code ...

logger = logging.getLogger(__name__)

# --- Abstract Repository Definition ---

class AbstractOrderRepository(ABC):
    """Interface abstraite pour le repository des Commandes."""

    @abstractmethod
    async def get_by_id(self, order_id: int) -> Optional[Order]:
        """Récupère une commande par son ID, incluant potentiellement ses items."""
        raise NotImplementedError

    @abstractmethod
    async def list_and_count_for_user(self, user_id: int, limit: int, offset: int) -> Tuple[List[Order], int]:
        """Liste les commandes pour un utilisateur donné avec pagination et retourne le total."""
        raise NotImplementedError
    
    @abstractmethod
    async def add(self, order_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Order:
        """Ajoute une nouvelle commande avec ses items."""
        raise NotImplementedError

    @abstractmethod
    async def update_status(self, order_id: int, status: str) -> Optional[Order]:
        """Met à jour le statut d'une commande."""
        raise NotImplementedError

# --- Dépendances Repository Implementation ---

async def get_order_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> AbstractOrderRepository:
    """
    Fournit une instance du repository de commandes.
    
    Args:
        session: Session de base de données asynchrone
        
    Returns:
        AbstractOrderRepository: Instance du repository de commandes
    """
    return SQLAlchemyOrderRepository(session)

OrderRepositoryDep = Annotated[AbstractOrderRepository, Depends(get_order_repository)]

# --- Dépendances CRUD ---

def get_order_crud(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> FastCRUD[Order]:
    """
    Fournit une instance de FastCRUD pour les commandes.
    
    Args:
        session: Session de base de données asynchrone
        
    Returns:
        FastCRUD[Order]: Instance de FastCRUD configurée pour le modèle Order
    """
    return FastCRUD(Order, session)

OrderCRUDDep = Annotated[FastCRUD[Order], Depends(get_order_crud)]

def get_order_item_crud(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> FastCRUD[OrderItem]:
    """
    Fournit une instance de FastCRUD pour les items de commande.
    
    Args:
        session: Session de base de données asynchrone
        
    Returns:
        FastCRUD[OrderItem]: Instance de FastCRUD configurée pour le modèle OrderItem
    """
    return FastCRUD(OrderItem, session)

OrderItemCRUDDep = Annotated[FastCRUD[OrderItem], Depends(get_order_item_crud)]

# --- Dépendances pour les autres repositories ---

def get_variant_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> AbstractProductVariantRepository:
    """
    Fournit une instance de SQLAlchemyProductVariantRepository.
    
    Args:
        session: Session de base de données asynchrone
        
    Returns:
        AbstractProductVariantRepository: Instance du repository de variants de produits
    """
    return SQLAlchemyProductVariantRepository(session)

def get_stock_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> AbstractStockRepository:
    """
    Fournit une instance de SQLAlchemyStockRepository.
    
    Args:
        session: Session de base de données asynchrone
        
    Returns:
        AbstractStockRepository: Instance du repository de stock
    """
    return SQLAlchemyStockRepository(session)

def get_address_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> AbstractAddressRepository:
    """
    Fournit une instance de AddressSQLRepository.
    
    Args:
        session: Session de base de données asynchrone
        
    Returns:
        AbstractAddressRepository: Instance du repository d'adresses
    """
    return AddressSQLRepository(session)

# --- Service Dependencies ---

VariantRepositoryDep = Annotated[AbstractProductVariantRepository, Depends(get_variant_repository)]
StockRepositoryDep = Annotated[AbstractStockRepository, Depends(get_stock_repository)]
AddressRepositoryDep = Annotated[AbstractAddressRepository, Depends(get_address_repository)]

# --- Dépendances Service ---

def get_order_service(
    order_repo: OrderRepositoryDep,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    address_service: Annotated[AddressService, Depends(get_address_service)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
    product_variant_service: Annotated[ProductVariantService, Depends(get_variant_service)],
    stock_service: Annotated[StockService, Depends(get_stock_service)]
) -> OrderService:
    """
    Fournit une instance du service de gestion des commandes.
    
    Args:
        order_repo: Instance du repository de commandes
        db: Session de base de données asynchrone
        address_service: Service de gestion des adresses
        email_service: Service d'envoi d'emails
        product_variant_service: Service de gestion des variants de produits
        stock_service: Service de gestion des stocks
        
    Returns:
        OrderService: Instance du service de gestion des commandes
    """
    logger.debug("Fourniture de OrderService")
    return OrderService(
        db=db,
        order_repository=order_repo,
        address_service=address_service,
        email_service=email_service,
        product_variant_service=product_variant_service,
        stock_service=stock_service
    )

OrderServiceDep = Annotated[OrderService, Depends(get_order_service)] 