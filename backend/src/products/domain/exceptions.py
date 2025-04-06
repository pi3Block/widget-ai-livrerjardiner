"""Exceptions spécifiques au domaine Product."""

from typing import Optional, List

class ProductDomainException(Exception):
    """Classe de base pour les exceptions du domaine Product."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class ProductNotFoundException(ProductDomainException):
    """Levée lorsqu'un produit spécifique n'est pas trouvé."""
    def __init__(self, product_id: int):
        super().__init__(f"Produit avec ID {product_id} non trouvé.")
        self.product_id = product_id

class CategoryNotFoundException(ProductDomainException):
    """Levée lorsqu'une catégorie spécifique n'est pas trouvée."""
    def __init__(self, category_id: int):
        super().__init__(f"Catégorie avec ID {category_id} non trouvée.")
        self.category_id = category_id

class TagNotFoundException(ProductDomainException):
    """Levée lorsqu'un tag spécifique n'est pas trouvé."""
    def __init__(self, tag_id: int):
        super().__init__(f"Tag avec ID {tag_id} non trouvé.")
        self.tag_id = tag_id

class VariantNotFoundException(ProductDomainException):
    """Levée lorsqu'une variante de produit spécifique n'est pas trouvée."""
    def __init__(self, variant_id: Optional[int] = None, sku: Optional[str] = None):
        if variant_id:
            super().__init__(f"Variante de produit avec ID {variant_id} non trouvée.")
            self.variant_id = variant_id
            self.sku = None
        elif sku:
             super().__init__(f"Variante de produit avec SKU {sku} non trouvée.")
             self.variant_id = None
             self.sku = sku
        else:
            super().__init__("Variante de produit non trouvée (aucun identifiant fourni).")
            self.variant_id = None
            self.sku = None

class StockNotFoundException(ProductDomainException):
    """Levée lorsque l'information de stock pour une variante n'est pas trouvée."""
    def __init__(self, variant_id: int):
        super().__init__(f"Information de stock non trouvée pour la variante ID {variant_id}.")
        self.variant_id = variant_id

class InsufficientStockException(ProductDomainException):
    """Levée lorsque le stock est insuffisant pour une opération."""
    def __init__(self, variant_id: int, requested: int, available: int):
        super().__init__(f"Stock insuffisant pour la variante ID {variant_id}. Demandé: {requested}, Disponible: {available}")
        self.variant_id = variant_id
        self.requested = requested
        self.available = available

class DuplicateSKUException(ProductDomainException):
    """Levée lors de la tentative de création d'une variante avec un SKU déjà existant."""
    def __init__(self, sku: str):
        super().__init__(f"Le SKU '{sku}' existe déjà.")
        self.sku = sku

class InvalidOperationException(ProductDomainException):
    """Levée pour une opération invalide (ex: SKU dupliqué, suppression impossible)."""
    pass

class ProductUpdateFailedException(ProductDomainException):
    """Levée lorsque la mise à jour d'un produit échoue."""
    pass

class ProductCreationFailedException(ProductDomainException):
    """Levée lorsque la création d'un produit échoue."""
    pass 