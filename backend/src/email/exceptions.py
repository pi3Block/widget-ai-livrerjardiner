"""Exceptions spécifiques au domaine Email."""

from typing import Optional

class EmailDomainException(Exception):
    """Classe de base pour les exceptions du domaine Email."""
    pass

class EmailSendingException(EmailDomainException):
    """Levée lorsqu'une erreur survient pendant la tentative d'envoi d'un email."""
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        full_message = f"Erreur lors de l'envoi de l'email: {message}"
        if original_exception:
            full_message += f" (Erreur originale: {original_exception})"
        super().__init__(full_message)
        self.original_exception = original_exception

class EmailConfigurationException(EmailDomainException):
     """Levée si la configuration du service email est invalide ou manquante."""
     pass

class EmailTemplateException(EmailDomainException):
    """Levée si une erreur survient lors du rendu du template email."""
    pass 