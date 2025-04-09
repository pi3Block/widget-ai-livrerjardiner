"""Exceptions spécifiques au module Quote."""

from typing import Optional, List

class QuoteDomainException(Exception):
    """Classe de base pour les exceptions du module Quote."""
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
    def __init__(self, detail: str = "Erreur lors de la création du devis."):
        super().__init__(detail)
        self.detail = detail

class DuplicateQuoteException(QuoteDomainException):
    """Levée en cas de tentative de création d'un devis qui violerait une contrainte d'unicité."""
    def __init__(self, detail: str = "Un devis similaire existe déjà."):
        super().__init__(detail)
        self.detail = detail

class QuoteUpdateException(QuoteDomainException):
    """Levée en cas d'erreur générale lors de la mise à jour d'un devis."""
    def __init__(self, quote_id: Optional[int] = None, detail: str = "Erreur lors de la mise à jour du devis."):
        message = f"Erreur MAJ devis{f' ID {quote_id}' if quote_id else ''}: {detail}"
        super().__init__(message)
        self.quote_id = quote_id
        self.detail = detail

class QuoteDeletionException(QuoteDomainException):
    """Levée en cas d'erreur lors de la suppression d'un devis."""
    def __init__(self, quote_id: Optional[int] = None, detail: str = "Erreur lors de la suppression du devis."):
        message = f"Erreur suppression devis{f' ID {quote_id}' if quote_id else ''}: {detail}"
        super().__init__(message)
        self.quote_id = quote_id
        self.detail = detail 