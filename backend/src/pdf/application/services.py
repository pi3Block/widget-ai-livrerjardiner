import logging
from typing import Dict, Any, Optional

# Domain
from src.pdf.domain.generator import AbstractPDFGenerator
from src.pdf.domain.exceptions import PDFGenerationException, TemplateNotFoundException

# Application (Types d'entrée potentiels)
# from src.quotes.application.schemas import QuoteResponse # Idéal

logger = logging.getLogger(__name__)

class PDFService:
    """Service applicatif pour la génération de documents PDF."""

    def __init__(self, pdf_generator: AbstractPDFGenerator):
        self.pdf_generator = pdf_generator
        logger.info("[PDFService] Initialisé.")

    async def generate_quote_pdf_from_data(
        self,
        quote_data: Dict[str, Any], # Prend un dict formaté
        output_path: Optional[str] = None
    ) -> bytes:
        """Génère un PDF de devis à partir d'un dictionnaire de données.
        
        Args:
            quote_data: Dictionnaire contenant les informations nécessaires 
                        (id, user, items, total_amount, created_at, etc.).
            output_path: Chemin optionnel pour sauvegarder le fichier.

        Returns:
            Contenu binaire du PDF.
            
        Raises:
            PDFGenerationException: Si la génération échoue.
        """
        quote_id = quote_data.get('id', 'inconnu')
        logger.info(f"[PDFService] Demande de génération PDF pour devis #{quote_id}.")
        
        try:
            # Note: L'implémentation ReportLab n'utilise pas de template HTML externe
            # mais l'interface le prévoyait. On ignore template_name pour ReportLab.
            pdf_bytes = await self.pdf_generator.generate_quote_pdf(
                quote_data=quote_data,
                output_path=output_path
            )
            return pdf_bytes
        except PDFGenerationException as e:
            logger.error(f"[PDFService] Échec génération PDF devis #{quote_id}: {e}")
            raise # Propage l'exception
        except Exception as e:
            logger.error(f"[PDFService] Erreur inattendue génération PDF devis #{quote_id}: {e}", exc_info=True)
            raise PDFGenerationException(f"Erreur inattendue: {e}", original_exception=e)

    # On pourrait ajouter ici une méthode qui prend un QuoteResponse DTO
    # et le transforme en dict avant d'appeler generate_quote_pdf_from_data
    # async def generate_quote_pdf_from_dto(self, quote_dto: QuoteResponse, ...) 