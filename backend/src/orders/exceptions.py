"""Exceptions spécifiques au domaine Order."""
from typing import Optional, List # Nécessaire pour l'import dans __init__.py

class OrderDomainException(Exception):
    """Classe de base pour les exceptions du domaine Order."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class OrderNotFoundException(OrderDomainException):
    """Levée lorsqu'une commande spécifique n'est pas trouvée."""
    def __init__(self, order_id: int):
        super().__init__(f"Commande avec ID {order_id} non trouvée.")
        self.order_id = order_id

class OrderUpdateForbiddenException(OrderDomainException):
     """Levée lorsqu'une opération de mise à jour est interdite (statut, utilisateur)."""
     pass

class InvalidOrderStatusException(OrderDomainException):
    """Levée lorsque le statut fourni pour une commande est invalide."""
    def __init__(self, status: str, allowed: List[str]):
        allowed_str = ", ".join(allowed)
        super().__init__(f"Le statut '{status}' est invalide. Statuts autorisés: {allowed_str}.")
        self.status = status
        self.allowed = allowed

class OrderCreationFailedException(OrderDomainException):
    """Levée lorsque la création de la commande échoue pour une raison spécifique (stock, validation...)."""
    pass

class InsufficientStockForOrderException(OrderDomainException):
    """Levée si le stock est insuffisant pour traiter un item de la commande."""
    def __init__(self, variant_id: int, sku: str, requested: int, available: int):
        super().__init__(f"Stock insuffisant pour '{sku}' (ID: {variant_id}). Demandé: {requested}, Disponible: {available}.")
        self.variant_id = variant_id
        self.sku = sku
        self.requested = requested
        self.available = available

class InsufficientStockException(Exception):
    """Exception levée lorsqu'il n'y a pas assez de stock pour une commande."""
    def __init__(self, message: str = "Stock insuffisant pour cette commande"):
        self.message = message
        super().__init__(self.message) 