class StockMovementNotFoundException(Exception):
    """Exception levée lorsqu'un mouvement de stock n'est pas trouvé."""
    def __init__(self, movement_id: int = None, message: str = "Mouvement de stock non trouvé"):
        self.movement_id = movement_id
        self.message = f"{message}{f' (ID: {movement_id})' if movement_id else ''}."
        super().__init__(self.message)

class StockMovementCreationFailedException(Exception):
    """Exception levée lors d'un échec de la création du mouvement de stock."""
    def __init__(self, message: str = "Échec de la création du mouvement de stock"):
        self.message = message
        super().__init__(self.message)

class InvalidStockMovementOperationException(Exception):
    """Exception pour des opérations invalides sur les mouvements de stock."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message) 