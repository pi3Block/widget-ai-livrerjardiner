from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastcrud import FastCRUD

from src.database import get_db_session
from .models import ProductVariant
from .service import ProductVariantService

# Importer les dépendances des autres services nécessaires
from src.products.models import Product # Modèle Product pour le CRUD
from src.stock.dependencies import get_stock_service
from src.tags.dependencies import get_tag_service


# Type hints pour les services dépendants
from src.stock.service import StockService
from src.tags.service import TagService

# CRUD pour ProductVariant
def get_variant_crud(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> FastCRUD[ProductVariant]:
    """
    Fournit une instance de FastCRUD pour les variants de produits.
    
    Args:
        session: Session de base de données asynchrone
        
    Returns:
        FastCRUD[ProductVariant]: Instance de FastCRUD configurée pour le modèle ProductVariant
    """
    return FastCRUD(ProductVariant, session)

VariantCRUDDep = Annotated[FastCRUD[ProductVariant], Depends(get_variant_crud)]

# CRUD pour Product (nécessaire pour la validation dans VariantService)
def get_product_crud(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> FastCRUD[Product]:
    """
    Fournit une instance de FastCRUD pour les produits.
    
    Args:
        session: Session de base de données asynchrone
        
    Returns:
        FastCRUD[Product]: Instance de FastCRUD configurée pour le modèle Product
    """
    return FastCRUD(Product, session)

ProductCRUDDep = Annotated[FastCRUD[Product], Depends(get_product_crud)]

# Service ProductVariant
def get_variant_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    variant_crud: Annotated[FastCRUD[ProductVariant], Depends(get_variant_crud)],
    product_crud: Annotated[FastCRUD[Product], Depends(get_product_crud)],
    stock_service: Annotated[StockService, Depends(get_stock_service)],
    tag_service: Annotated[TagService, Depends(get_tag_service)]
) -> ProductVariantService:
    """
    Fournit une instance du service de gestion des variants de produits.
    
    Args:
        db: Session de base de données asynchrone
        variant_crud: Instance de FastCRUD pour les variants de produits
        product_crud: Instance de FastCRUD pour les produits
        stock_service: Service de gestion des stocks
        tag_service: Service de gestion des tags
        
    Returns:
        ProductVariantService: Instance du service de gestion des variants de produits
    """
    return ProductVariantService(
        db=db,
        variant_crud=variant_crud,
        product_crud=product_crud,
        stock_service=stock_service,
        tag_service=tag_service
    )

VariantServiceDep = Annotated[ProductVariantService, Depends(get_variant_service)] 