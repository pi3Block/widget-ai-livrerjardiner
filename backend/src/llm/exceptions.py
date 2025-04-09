"""
Exceptions personnalisées pour le module LLM.

Ce module définit les exceptions spécifiques au domaine LLM
pour une meilleure gestion des erreurs.
"""
from typing import Optional


class LLMError(Exception):
    """Classe de base pour les exceptions du module LLM."""
    pass


class LLMParsingError(LLMError):
    """Levée quand le parsing de l'intention échoue."""
    
    def __init__(self, message: str, raw_response: Optional[str] = None):
        self.raw_response = raw_response
        super().__init__(message)


class LLMRequestError(LLMError):
    """Levée quand une requête au LLM échoue."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class LLMTimeoutError(LLMError):
    """Levée quand une requête au LLM expire."""
    pass


class InvalidIntentError(LLMError):
    """Levée quand l'intention parsée n'est pas valide."""
    
    def __init__(self, intent: str, message: str):
        self.intent = intent
        super().__init__(f"Intent '{intent}' invalide: {message}")


class QuoteCreationError(LLMError):
    """Levée quand la création d'un devis échoue."""
    
    def __init__(self, message: str, items: Optional[list] = None):
        self.items = items
        super().__init__(message)


class OrderCreationError(LLMError):
    """Levée quand la création d'une commande échoue."""
    
    def __init__(self, message: str, items: Optional[list] = None):
        self.items = items
        super().__init__(message)
