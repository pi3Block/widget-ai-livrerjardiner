"""
Constantes pour le module de gestion des stocks.
"""

# Types de mouvements de stock
STOCK_MOVEMENT_IN = "IN"
STOCK_MOVEMENT_OUT = "OUT"
STOCK_MOVEMENT_ADJUSTMENT = "ADJUSTMENT"

# Statuts de stock
STOCK_STATUS_AVAILABLE = "AVAILABLE"
STOCK_STATUS_LOW = "LOW"
STOCK_STATUS_OUT = "OUT"
STOCK_STATUS_RESERVED = "RESERVED"

# Seuils d'alerte
STOCK_LOW_THRESHOLD = 5
STOCK_CRITICAL_THRESHOLD = 2

# Messages d'erreur
ERROR_STOCK_INSUFFICIENT = "Stock insuffisant pour cette opération"
ERROR_INVALID_QUANTITY = "Quantité invalide"
ERROR_PRODUCT_NOT_FOUND = "Produit non trouvé" 