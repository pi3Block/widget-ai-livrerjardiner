"""
Utilitaires pour le module de gestion des stocks.
"""
from datetime import datetime
from typing import Optional

from .constants import (
    STOCK_STATUS_AVAILABLE,
    STOCK_STATUS_LOW,
    STOCK_STATUS_OUT,
    STOCK_LOW_THRESHOLD,
    STOCK_CRITICAL_THRESHOLD
)

def calculate_stock_status(quantity: int) -> str:
    """
    Calcule le statut du stock en fonction de la quantité disponible.
    
    Args:
        quantity: Quantité disponible en stock
        
    Returns:
        str: Statut du stock (AVAILABLE, LOW, OUT)
    """
    if quantity <= 0:
        return STOCK_STATUS_OUT
    elif quantity <= STOCK_CRITICAL_THRESHOLD:
        return STOCK_STATUS_OUT
    elif quantity <= STOCK_LOW_THRESHOLD:
        return STOCK_STATUS_LOW
    return STOCK_STATUS_AVAILABLE

def format_stock_movement_reference(
    movement_type: str,
    product_id: int,
    timestamp: Optional[datetime] = None
) -> str:
    """
    Génère une référence unique pour un mouvement de stock.
    
    Args:
        movement_type: Type de mouvement (IN, OUT, ADJUSTMENT)
        product_id: ID du produit
        timestamp: Horodatage du mouvement (optionnel)
        
    Returns:
        str: Référence formatée
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    return f"{movement_type}-{product_id}-{timestamp.strftime('%Y%m%d%H%M%S')}"

def validate_stock_quantity(quantity: int) -> bool:
    """
    Valide une quantité de stock.
    
    Args:
        quantity: Quantité à valider
        
    Returns:
        bool: True si la quantité est valide, False sinon
    """
    return isinstance(quantity, int) and quantity >= 0

def calculate_stock_value(quantity: int, unit_price: float) -> float:
    """
    Calcule la valeur totale du stock.
    
    Args:
        quantity: Quantité en stock
        unit_price: Prix unitaire
        
    Returns:
        float: Valeur totale du stock
    """
    return quantity * unit_price 