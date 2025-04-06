"""Exceptions spécifiques au domaine Quote."""

from typing import Optional, List

class QuoteDomainException(Exception):
    """Classe de base pour les exceptions du domaine Quote."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class QuoteNotFoundException(QuoteDomainException):
    """Levée lorsqu'un devis spécifique n'est pas trouvé."""
    def __init__(self, quote_id: int):
        super().__init__(f"Devis avec ID {quote_id} non trouvé.")
        self.quote_id = quote_id

class QuoteUpdateForbiddenException(QuoteDomainException):
     """Levée lorsqu'une opération de mise à jour est interdite (statut, utilisateur)."""
     pass

class InvalidQuoteStatusException(QuoteDomainException):
    """Levée lorsque le statut fourni pour un devis est invalide."""
    def __init__(self, status: str, allowed: List[str]):
        allowed_str = ", ".join(allowed)
        super().__init__(f"Le statut '{status}' est invalide. Statuts autorisés: {allowed_str}.")
        self.status = status
        self.allowed = allowed

class QuoteCreationFailedException(QuoteDomainException):
    """Levée en cas d'erreur lors de la création d'un devis."""
    def __init__(self, message: str = "Erreur lors de la création du devis."):
        super().__init__(message) 