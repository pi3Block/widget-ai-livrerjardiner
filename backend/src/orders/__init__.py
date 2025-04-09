"""
Module Orders - Gestion des commandes
"""

# Exposer les modèles et schémas pour faciliter les imports
from src.orders.models import (
    Order, OrderItem,
    OrderCreate, OrderResponse, OrderUpdate, PaginatedOrderResponse,
    OrderItemCreate, OrderItemResponse
)

__all__ = [
    "Order", "OrderItem",
    "OrderCreate", "OrderResponse", "OrderUpdate", "PaginatedOrderResponse",
    "OrderItemCreate", "OrderItemResponse"
] 