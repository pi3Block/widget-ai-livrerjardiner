"""
Exceptions personnalisées pour le module de gestion des stocks.
"""

class StockError(Exception):
    """Classe de base pour les exceptions liées au stock."""
    pass

class InsufficientStockError(StockError):
    """Levée lorsque le stock est insuffisant pour une opération."""
    def __init__(self, product_id: int, requested: int, available: int):
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Stock insuffisant pour le produit {product_id}. "
            f"Demandé: {requested}, Disponible: {available}"
        )

class InvalidStockMovementError(StockError):
    """Levée lorsque le mouvement de stock est invalide."""
    def __init__(self, message: str):
        super().__init__(f"Mouvement de stock invalide: {message}")

class StockNotFoundError(StockError):
    """Levée lorsque l'entrée de stock n'est pas trouvée."""
    def __init__(self, stock_id: int):
        super().__init__(f"Entrée de stock {stock_id} non trouvée")

class StockMovementNotFoundError(StockError):
    """Levée lorsque le mouvement de stock n'est pas trouvé."""
    def __init__(self, movement_id: int):
        super().__init__(f"Mouvement de stock {movement_id} non trouvé")

class StockValidationError(StockError):
    """Levée lorsque la validation des données de stock échoue."""
    def __init__(self, message: str):
        super().__init__(f"Erreur de validation du stock: {message}") 