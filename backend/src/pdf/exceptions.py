"""Exceptions spécifiques au domaine PDF."""

from typing import Optional

class PDFDomainException(Exception):
    """Classe de base pour les exceptions du domaine PDF."""
    pass

class PDFGenerationException(PDFDomainException):
    """Levée lorsqu'une erreur survient pendant la génération d'un PDF."""
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        full_message = f"Erreur lors de la génération du PDF: {message}"
        if original_exception:
            full_message += f" (Erreur originale: {original_exception})"
        super().__init__(full_message)
        self.original_exception = original_exception

class TemplateNotFoundException(PDFDomainException):
     """Levée si le template HTML pour le PDF est introuvable."""
     def __init__(self, template_name: str, search_path: str):
         super().__init__(f"Template PDF '{template_name}' non trouvé dans {search_path}.")
         self.template_name = template_name
         self.search_path = search_path 