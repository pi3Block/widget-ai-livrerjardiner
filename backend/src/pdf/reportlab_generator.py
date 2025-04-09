import logging
import os
import io
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

# ReportLab Imports
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

# Configuration (Ajout import)
from src.pdf.config import PDFSettings

# Domain
from pdf.generator import AbstractPDFGenerator
from pdf.exceptions import PDFGenerationException
from src.pdf.domain.models import PDFQuoteData

logger = logging.getLogger(__name__)

# Suppression des constantes globales définies ici
# LOGO_PATH = \"backend/static/logo.png\"
# TMP_PDF_DIR = \"temp_pdfs\" 
# COMPANY_INFO_HTML = (
#     \"<b>LivrerJardiner.fr</b><br/>\"
#     \"123 Rue des Jardins, 75000 Paris<br/>\"
#     \"Email : contact@livrerjardiner.fr<br/>\"
#     \"Tél : +33 1 23 45 67 89\"
# )
# FOOTER_TEXT = \"LivrerJardiner.fr - Votre partenaire pour un jardin fleuri\"
# PRIMARY_COLOR = colors.HexColor(\"#5a9a1f\")

class ReportLabPDFGenerator(AbstractPDFGenerator):
    """Implémentation du générateur PDF utilisant ReportLab."""

    def __init__(self, settings: PDFSettings):
        """Initialise le générateur ReportLab avec sa configuration.
        
        Args:
            settings: L'objet de configuration PDFSettings.
        """
        self.settings = settings
        # Convertir la couleur HEX en objet couleur ReportLab une seule fois
        self.primary_color = colors.HexColor(settings.PRIMARY_COLOR_HEX)
        logger.info("[ReportLabPDFGenerator] Initialisé avec la configuration.")

    async def generate_quote_pdf(
        self,
        quote_data: PDFQuoteData,
        output_path: Optional[str] = None
    ) -> bytes:
        """Génère un PDF de devis en utilisant ReportLab.

        Construit le document PDF à partir des données fournies, 
        ajoute un logo, les informations de l'entreprise, 
        les détails du client, le tableau des articles, et un pied de page.

        Args:
            quote_data: Objet PDFQuoteData contenant les informations du devis.
            output_path: Chemin optionnel où sauvegarder le fichier PDF généré.

        Returns:
            Les octets (bytes) du document PDF généré.

        Raises:
            PDFGenerationException: Si une erreur survient pendant la construction du PDF.
        """
        
        quote_id = quote_data.id
        logger.info(f"[PDFGen] Génération PDF devis #{quote_id}")
        
        buffer = io.BytesIO() # Buffer mémoire pour le PDF
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Styles personnalisés utilisant les settings
        title_style = styles["Heading1"]
        title_style.textColor = self.primary_color # Utilisation de la couleur convertie
        normal_style = styles["Normal"]
        footer_style = ParagraphStyle(name="Footer", fontSize=10, textColor=colors.gray, alignment=1)
        bold_style = ParagraphStyle(name="Bold", parent=normal_style, fontName='Helvetica-Bold')
        company_info_style = ParagraphStyle(name='CompanyInfo', parent=normal_style, alignment=2)

        # --- Construction du contenu du PDF --- 
        
        # 1. Logo (utilise settings.LOGO_PATH)
        try:
             if os.path.exists(self.settings.LOGO_PATH):
                logo = Image(self.settings.LOGO_PATH, width=1.5*inch, height=0.75*inch)
                logo.hAlign = 'LEFT'
                elements.append(logo)
             else:
                logger.warning(f"[PDFGen] Logo non trouvé : {self.settings.LOGO_PATH}")
                elements.append(Paragraph("LivrerJardiner.fr", title_style))
        except Exception as img_err:
            logger.error(f"[PDFGen] Erreur chargement logo: {img_err}. Utilisation titre.", exc_info=True)
            elements.append(Paragraph("LivrerJardiner.fr", title_style))
        elements.append(Spacer(1, 0.1*inch))

        # 2. Infos Compagnie (utilise settings.COMPANY_INFO_HTML)
        company_info = Paragraph(self.settings.COMPANY_INFO_HTML, company_info_style)
        elements.append(company_info)
        elements.append(Spacer(1, 0.2*inch))

        # 3. Titre Devis et Date
        elements.append(Paragraph(f"Devis #{quote_id}", styles["h2"]))
        quote_date_str = quote_data.created_at.strftime('%d/%m/%Y')
        elements.append(Paragraph(f"Date : {quote_date_str}", normal_style))
        elements.append(Spacer(1, 0.1*inch))

        # 4. Infos Client
        user_info = quote_data.user
        user_name = user_info.name
        user_email = user_info.email
        client_text = f"<b>Client :</b> {user_name}"
        if user_email:
            client_text += f" ({user_email})"
        elements.append(Paragraph(client_text, normal_style))
        elements.append(Spacer(1, 0.2*inch))

        # 5. Tableau des Items
        table_data = [
            [
                Paragraph("<b>Référence (SKU)</b>", normal_style), 
                Paragraph("<b>Description</b>", normal_style),
                Paragraph("<b>Quantité</b>", normal_style), 
                Paragraph("<b>Prix Unitaire (€)</b>", normal_style), 
                Paragraph("<b>Total Ligne (€)</b>", normal_style)
            ]
        ]
        grand_total = quote_data.total_amount
        items = quote_data.items
        
        for item in items:
            # Extrait les infos de l'item (structure basée sur celle passée par ChatService)
            sku = item.variant_sku
            description = item.variant_details.name
            quantity = item.quantity
            unit_price = item.price_at_quote
            line_total = quantity * unit_price
            
            table_data.append([
                Paragraph(sku, normal_style),
                Paragraph(description, normal_style),
                str(quantity),
                f"{unit_price:.2f}",
                f"{line_total:.2f}"
            ])

        table_data.append([
            Paragraph(" ", normal_style),
            Paragraph(" ", normal_style),
            Paragraph(" ", normal_style),
            Paragraph("<b>Total Devis (€)</b>", bold_style),
            Paragraph(f"<b>{grand_total:.2f}</b>", bold_style)
        ])
        
        table = Table(table_data, colWidths=[1.5*inch, 2.5*inch, 0.8*inch, 1.2*inch, 1.5*inch])
        
        # Utilisation de self.primary_color
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -2), 1, colors.darkgrey),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (3, -1), (-1, -1), 1, colors.darkgrey),
            ('ALIGN', (3, -1), (-1, -1), 'RIGHT'),
            ('VALIGN', (3, -1), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, -1), (-1, -1), 12),
        ])
        table.setStyle(table_style)
        elements.append(table)
        elements.append(Spacer(1, 0.5*inch))

        # 6. Notes finales
        elements.append(Paragraph(
            "Merci de valider ce devis pour confirmer votre commande.<br/>"
            "Pour toute question, contactez-nous à contact@livrerjardiner.fr.", 
            normal_style
        ))

        # --- Fonction pour le Footer (utilise settings.FOOTER_TEXT) ---
        def add_footer(canvas, doc):
            """Ajoute un pied de page à chaque page du document PDF.

            Args:
                canvas: Le canevas ReportLab sur lequel dessiner.
                doc: Le document PDF en cours de construction.
            """
            canvas.saveState()
            footer = Paragraph(self.settings.FOOTER_TEXT, footer_style)
            w, h = footer.wrap(doc.width, doc.bottomMargin)
            footer.drawOn(canvas, doc.leftMargin, h)
            canvas.restoreState()

        # --- Génération du PDF dans le buffer --- 
        try:
            doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            logger.info(f"[PDFGen] PDF devis #{quote_id} généré en mémoire ({len(pdf_bytes)} bytes).")
            
            # Sauvegarder si output_path est fourni (utilise settings.TMP_PDF_DIR)
            if output_path:
                try:
                    output_dir = os.path.dirname(output_path)
                    if not output_dir: # Si aucun dossier spécifié, utiliser le dossier tmp par défaut
                        output_dir = self.settings.TMP_PDF_DIR
                        # Recréer le chemin complet
                        output_path = os.path.join(output_dir, os.path.basename(output_path))
                        
                    os.makedirs(output_dir, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(pdf_bytes)
                    logger.info(f"[PDFGen] PDF devis #{quote_id} sauvegardé dans: {output_path}")
                except Exception as save_err:
                    logger.error(f"[PDFGen] Erreur sauvegarde PDF dans {output_path}: {save_err}", exc_info=True)
                    pass
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"[PDFGen] Erreur ReportLab build() pour devis #{quote_id}: {e}", exc_info=True)
            raise PDFGenerationException(f"Erreur lors de la construction du PDF: {e}", original_exception=e) 

    # Implémentation de la méthode generate_pdf à faire si nécessaire
    async def generate_pdf(
        self,
        template_name: str, 
        context: Dict[str, Any], # Note: context devrait idéalement être un modèle Pydantic aussi
        output_path: Optional[str] = None
    ) -> bytes:
        """Génère un PDF générique (non implémenté pour ReportLab sans HTML)."""
        logger.warning("[ReportLabPDFGenerator] La méthode generate_pdf (template HTML) n'est pas implémentée.")
        raise NotImplementedError("ReportLabGenerator n'implémente pas la génération via template HTML.") 