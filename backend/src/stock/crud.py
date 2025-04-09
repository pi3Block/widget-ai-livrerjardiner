from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
import logging
from sqlalchemy import func

# Import du modèle de table SQLModel
from .models import Stock, StockUpdate
# Importer les exceptions nécessaires (à créer si elles n'existent pas)
from src.products.domain.exceptions import StockNotFoundException, InsufficientStockException

logger = logging.getLogger(__name__)

async def get_stock_for_variant(db: AsyncSession, product_variant_id: int) -> Optional[Stock]:
    """Récupère l'enregistrement de stock pour une variante de produit."""
    result = await db.execute(
        select(Stock).filter(Stock.product_variant_id == product_variant_id)
    )
    stock = result.scalars().first()
    # Pas de log warning ici, le service appelant décidera quoi faire si None est retourné
    return stock

async def update_stock_quantity(db: AsyncSession, product_variant_id: int, quantity_change: int) -> Stock:
    """Met à jour la quantité de stock pour une variante et retourne l'objet mis à jour.
       quantity_change peut être positif (ajout) ou négatif (retrait).
       Lève StockNotFoundException si la variante n'a pas d'entrée de stock.
       Lève InsufficientStockException si la mise à jour résulte en un stock négatif.
    """
    stock = await get_stock_for_variant(db, product_variant_id)
    if not stock:
        logger.error(f"Tentative de mise à jour du stock pour variant_id {product_variant_id} inexistant.")
        raise StockNotFoundException(variant_id=product_variant_id)

    # Mettre à jour la quantité
    new_quantity = stock.quantity + quantity_change
    if new_quantity < 0:
         logger.error(f"Stock insuffisant pour variant_id {product_variant_id}. Demandé: {-quantity_change}, Disponible: {stock.quantity}")
         raise InsufficientStockException(variant_id=product_variant_id, requested=-quantity_change, available=stock.quantity)

    stock.quantity = new_quantity
    # Laisser le trigger gérer last_updated

    await db.flush() # Flush pour envoyer les changements à la DB et permettre la détection d'erreurs
    # Pas besoin de refresh ici en général, sauf si on a besoin de last_updated immédiatement
    logger.info(f"Stock mis à jour pour variant_id {product_variant_id}. Nouvelle quantité: {stock.quantity}")
    return stock

async def list_low_stock(
    db: AsyncSession, 
    threshold: int, 
    limit: int = 50, 
    offset: int = 0
) -> Tuple[List[Stock], int]:
    """Liste les entrées de stock dont la quantité est inférieure ou égale au seuil.
    
    Args:
        db: Session de base de données
        threshold: Seuil de stock bas
        limit: Nombre maximum d'éléments à retourner
        offset: Offset pour la pagination
        
    Returns:
        Tuple contenant la liste des stocks et le nombre total
    """
    # Requête pour compter le total
    count_query = select(Stock).filter(Stock.quantity <= threshold)
    total = await db.scalar(select(func.count()).select_from(count_query.subquery()))
    
    # Requête principale avec pagination
    query = (
        select(Stock)
        .filter(Stock.quantity <= threshold)
        .order_by(Stock.quantity.asc())  # Trier par quantité croissante
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    stocks = result.scalars().all()
    
    return stocks, total

async def update_stock_details(
    db: AsyncSession, 
    product_variant_id: int, 
    update_data: dict
) -> Stock:
    """Met à jour les détails du stock pour une variante.
    
    Args:
        db: Session de base de données
        product_variant_id: ID de la variante produit
        update_data: Dictionnaire contenant les champs à mettre à jour
        
    Returns:
        Stock mis à jour
        
    Raises:
        StockNotFoundException: Si le stock n'existe pas
        ValueError: Si la quantité est négative
    """
    stock = await get_stock_for_variant(db, product_variant_id)
    if not stock:
        raise StockNotFoundException(variant_id=product_variant_id)
        
    # Vérifier la quantité si elle est fournie
    if "quantity" in update_data and update_data["quantity"] < 0:
        raise ValueError("La quantité de stock ne peut pas être négative")
        
    # Appliquer les mises à jour
    for key, value in update_data.items():
        setattr(stock, key, value)
        
    await db.flush()
    await db.refresh(stock)
    
    return stock

async def get_stocks_for_variants(
    db: AsyncSession, 
    variant_ids: List[int]
) -> List[Stock]:
    """Récupère les stocks pour une liste de variantes.
    
    Args:
        db: Session de base de données
        variant_ids: Liste des IDs de variantes
        
    Returns:
        Liste des stocks correspondants
    """
    if not variant_ids:
        return []
        
    query = select(Stock).filter(Stock.product_variant_id.in_(variant_ids))
    result = await db.execute(query)
    return result.scalars().all()

# Potentiellement ajouter d'autres fonctions si nécessaire (ex: bulk_update, create_initial_stock)
