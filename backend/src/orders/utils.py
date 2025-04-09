"""
Utilitaires pour le module de gestion des commandes.
"""
from datetime import datetime
from typing import List, Optional

from .constants import (
    ORDER_STATUS_DRAFT,
    ORDER_STATUS_PENDING,
    ORDER_STATUS_CONFIRMED,
    ORDER_STATUS_PROCESSING,
    ORDER_STATUS_SHIPPED,
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_REFUNDED,
    MAX_ORDER_ITEMS,
    MIN_ORDER_AMOUNT,
    MAX_ORDER_AMOUNT
)

def generate_order_reference(order_id: int, timestamp: Optional[datetime] = None) -> str:
    """
    Génère une référence unique pour une commande.
    
    Args:
        order_id: ID de la commande
        timestamp: Horodatage de la commande (optionnel)
        
    Returns:
        str: Référence formatée
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    return f"ORD-{order_id:06d}-{timestamp.strftime('%Y%m%d')}"

def validate_order_amount(amount: float) -> bool:
    """
    Valide le montant total d'une commande.
    
    Args:
        amount: Montant à valider
        
    Returns:
        bool: True si le montant est valide, False sinon
    """
    return MIN_ORDER_AMOUNT <= amount <= MAX_ORDER_AMOUNT

def validate_order_items_count(items_count: int) -> bool:
    """
    Valide le nombre d'articles dans une commande.
    
    Args:
        items_count: Nombre d'articles
        
    Returns:
        bool: True si le nombre est valide, False sinon
    """
    return 0 < items_count <= MAX_ORDER_ITEMS

def get_next_order_status(current_status: str) -> Optional[str]:
    """
    Détermine le prochain statut possible pour une commande.
    
    Args:
        current_status: Statut actuel de la commande
        
    Returns:
        Optional[str]: Prochain statut possible ou None si aucun
    """
    status_flow = {
        ORDER_STATUS_DRAFT: ORDER_STATUS_PENDING,
        ORDER_STATUS_PENDING: ORDER_STATUS_CONFIRMED,
        ORDER_STATUS_CONFIRMED: ORDER_STATUS_PROCESSING,
        ORDER_STATUS_PROCESSING: ORDER_STATUS_SHIPPED,
        ORDER_STATUS_SHIPPED: ORDER_STATUS_DELIVERED,
        ORDER_STATUS_DELIVERED: None,
        ORDER_STATUS_CANCELLED: None,
        ORDER_STATUS_REFUNDED: None
    }
    return status_flow.get(current_status)

def calculate_order_total(items: List[dict]) -> float:
    """
    Calcule le montant total d'une commande.
    
    Args:
        items: Liste des articles de la commande
        
    Returns:
        float: Montant total
    """
    return sum(item.get('price', 0) * item.get('quantity', 0) for item in items) 