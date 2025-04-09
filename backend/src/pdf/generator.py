from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

# Ajout de l'import du modèle
from .domain.models import PDFQuoteData

class AbstractPDFGenerator(ABC):
    """Interface abstraite pour un générateur de documents PDF.
    Approche orientée données, l'implémentation gère la mise en page.
    """

    @abstractmethod
    async def generate_quote_pdf(
        self,
        quote_data: PDFQuoteData, # Modification du type de dict vers PDFQuoteData
        output_path: Optional[str] = None # Chemin où sauvegarder le PDF (optionnel)
    ) -> bytes:
        """Génère le PDF d'un devis.

        Args:
            quote_data: Objet PDFQuoteData contenant les données formatées pour le devis.
            output_path: Si fourni, sauvegarde le PDF à ce chemin.
                         Sinon, le contenu binaire est uniquement retourné.

        Returns:
            Le contenu binaire du PDF généré.

        Raises:
            PDFGenerationException: Si une erreur survient durant la génération.
        """
        raise NotImplementedError

    # Ajouter d'autres méthodes pour d'autres types de PDF si nécessaire
    # Ex: async def generate_invoice_pdf(...)

    @abstractmethod
    async def generate_pdf(
        self,
        template_name: str, # Nom du template HTML à utiliser
        context: Dict[str, Any], # Données à injecter dans le template
        output_path: Optional[str] = None # Chemin où sauvegarder le PDF (optionnel)
    ) -> bytes:
        """Génère un PDF à partir d'un template HTML et de données.

        Args:
            template_name: Nom du fichier template HTML (sans chemin).
            context: Dictionnaire contenant les données pour le template.
            output_path: Si fourni, sauvegarde le PDF à ce chemin. 
                         Sinon, le contenu binaire est uniquement retourné.

        Returns:
            Le contenu binaire du PDF généré.

        Raises:
            PDFGenerationException: Si une erreur survient durant la génération.
            TemplateNotFoundException: Si le template n'est pas trouvé.
        """
        raise NotImplementedError 