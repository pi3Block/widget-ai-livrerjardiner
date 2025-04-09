"""
Exceptions spécifiques au module product_variants.

Ce fichier contient les exceptions personnalisées utilisées
dans le module product_variants.
"""

class ProductVariantException(Exception):
    """Classe de base pour les exceptions du module product_variants."""
    pass


class VariantNotFoundException(ProductVariantException):
    """Exception levée lorsqu'une variante de produit n'est pas trouvée."""
    
    def __init__(self, variant_id: int = None, sku: str = None):
        self.variant_id = variant_id
        self.sku = sku
        message = "Variante de produit non trouvée"
        if variant_id:
            message += f" avec l'ID {variant_id}"
        if sku:
            message += f" avec le SKU {sku}"
        super().__init__(message)


class DuplicateSKUException(ProductVariantException):
    """Exception levée lorsqu'un SKU est déjà utilisé."""
    
    def __init__(self, sku: str):
        self.sku = sku
        super().__init__(f"Le SKU {sku} est déjà utilisé par une autre variante")


class InvalidVariantDataException(ProductVariantException):
    """Exception levée lorsque les données d'une variante sont invalides."""
    
    def __init__(self, message: str):
        super().__init__(f"Données de variante invalides: {message}")


class VariantUpdateException(ProductVariantException):
    """Exception levée lors de la mise à jour d'une variante."""
    
    def __init__(self, variant_id: int, message: str):
        self.variant_id = variant_id
        super().__init__(f"Erreur lors de la mise à jour de la variante {variant_id}: {message}")


class VariantDeleteException(ProductVariantException):
    """Exception levée lors de la suppression d'une variante."""
    
    def __init__(self, variant_id: int, message: str):
        self.variant_id = variant_id
        super().__init__(f"Erreur lors de la suppression de la variante {variant_id}: {message}")

class StockNotFoundException(ProductVariantDomainException):
    """Levée lorsqu'une information de stock n'est pas trouvée."""
    def __init__(self, variant_id: int):
        super().__init__(f"Information de stock non trouvée pour la variante {variant_id}.")
        self.variant_id = variant_id 