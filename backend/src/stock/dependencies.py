from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastcrud import FastCRUD

# Import de la session DB
from src.database import get_db_session

# Import du service Stock
from src.stock.models import Stock
from src.stock.service import StockService

def get_stock_crud(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> FastCRUD[Stock]:
    """
    Fournit une instance de FastCRUD pour les stocks.
    
    Args:
        session: Session de base de données asynchrone
        
    Returns:
        FastCRUD[Stock]: Instance de FastCRUD configurée pour le modèle Stock
    """
    return FastCRUD(Stock, session)

def get_stock_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    stock_crud: Annotated[FastCRUD[Stock], Depends(get_stock_crud)]
) -> StockService:
    """
    Fournit une instance du service de gestion des stocks.
    
    Args:
        db: Session de base de données asynchrone
        stock_crud: Instance de FastCRUD pour les stocks
        
    Returns:
        StockService: Instance du service de gestion des stocks
    """
    return StockService(db=db, stock_crud=stock_crud) 