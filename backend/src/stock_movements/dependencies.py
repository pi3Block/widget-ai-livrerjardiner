import logging
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastcrud import FastCRUD

from src.database import get_db_session
from src.stock_movements.models import StockMovement
from src.stock_movements.service import StockMovementService

logger = logging.getLogger(__name__)

# CRUD pour StockMovement
def get_movement_crud(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> FastCRUD[StockMovement]:
    """
    Fournit une instance de FastCRUD pour les mouvements de stock.
    
    Args:
        session: Session de base de données asynchrone
        
    Returns:
        FastCRUD[StockMovement]: Instance de FastCRUD configurée pour le modèle StockMovement
    """
    logger.debug("Providing FastCRUD[StockMovement]")
    return FastCRUD(StockMovement, session)

MovementCRUDDep = Annotated[FastCRUD[StockMovement], Depends(get_movement_crud)]

# Service StockMovement
def get_stock_movement_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    movement_crud: Annotated[FastCRUD[StockMovement], Depends(get_movement_crud)]
) -> StockMovementService:
    """
    Fournit une instance du service de gestion des mouvements de stock.
    
    Args:
        db: Session de base de données asynchrone
        movement_crud: Instance de FastCRUD pour les mouvements de stock
        
    Returns:
        StockMovementService: Instance du service de gestion des mouvements de stock
    """
    logger.debug("Providing StockMovementService")
    return StockMovementService(db=db, movement_crud=movement_crud)

StockMovementServiceDep = Annotated[StockMovementService, Depends(get_stock_movement_service)] 