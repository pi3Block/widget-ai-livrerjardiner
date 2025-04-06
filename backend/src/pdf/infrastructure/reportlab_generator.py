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

# Domain
from src.pdf.domain.generator import AbstractPDFGenerator
from src.pdf.domain.exceptions import PDFGenerationException

logger = logging.getLogger(__name__)

# Constantes de style ou configuration (pourraient être externes)
LOGO_PATH = "backend/static/logo.png"
TMP_PDF_DIR = "temp_pdfs" # Dossier pour sauvegarde temporaire si path fourni
COMPANY_INFO_HTML = (
    "<b>LivrerJardiner.fr</b><br/>"
    "123 Rue des Jardins, 75000 Paris<br/>"
    "Email : contact@livrerjardiner.fr<br/>"
    "Tél : +33 1 23 45 67 89"
)
FOOTER_TEXT = "LivrerJardiner.fr - Votre partenaire pour un jardin fleuri"
PRIMARY_COLOR = colors.HexColor("#5a9a1f")

class ReportLabPDFGenerator(AbstractPDFGenerator):
    """Implémentation du générateur PDF utilisant ReportLab."""

    def __init__(self):
        # Pas d'état spécifique nécessaire pour l'instant
        logger.info("[ReportLabPDFGenerator] Initialisé.")

    async def generate_quote_pdf(
        self,
        quote_data: Dict[str, Any], 
        output_path: Optional[str] = None
    ) -> bytes:
        
        quote_id = quote_data.get('id', 'N/A')
        logger.info(f"[PDFGen] Génération PDF devis #{quote_id}")
        
        buffer = io.BytesIO() # Buffer mémoire pour le PDF
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Styles personnalisés
        title_style = styles["Heading1"]
        title_style.textColor = PRIMARY_COLOR
        normal_style = styles["Normal"]
        footer_style = ParagraphStyle(name="Footer", fontSize=10, textColor=colors.gray, alignment=1)
        bold_style = ParagraphStyle(name="Bold", parent=normal_style, fontName='Helvetica-Bold')
        company_info_style = ParagraphStyle(name='CompanyInfo', parent=normal_style, alignment=2)

        # --- Construction du contenu du PDF --- 
        
        # 1. Logo
        try:
             if os.path.exists(LOGO_PATH):
                logo = Image(LOGO_PATH, width=1.5*inch, height=0.75*inch)
                logo.hAlign = 'LEFT'
                elements.append(logo)
             else:
                logger.warning(f"[PDFGen] Logo non trouvé : {LOGO_PATH}")
                elements.append(Paragraph("LivrerJardiner.fr", title_style))
        except Exception as img_err:
            logger.error(f"[PDFGen] Erreur chargement logo: {img_err}. Utilisation titre.", exc_info=True)
            elements.append(Paragraph("LivrerJardiner.fr", title_style))
        elements.append(Spacer(1, 0.1*inch))

        # 2. Infos Compagnie
        company_info = Paragraph(COMPANY_INFO_HTML, company_info_style)
        elements.append(company_info)
        elements.append(Spacer(1, 0.2*inch))

        # 3. Titre Devis et Date
        elements.append(Paragraph(f"Devis #{quote_id}", styles["h2"]))
        quote_date_str = quote_data.get('created_at', datetime.utcnow()).strftime('%d/%m/%Y')
        elements.append(Paragraph(f"Date : {quote_date_str}", normal_style))
        elements.append(Spacer(1, 0.1*inch))

        # 4. Infos Client
        user_info = quote_data.get('user', {})
        user_name = user_info.get('name', 'Client')
        user_email = user_info.get('email', '')
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
        grand_total = Decimal(quote_data.get('total_amount', 0))
        items = quote_data.get('items', [])
        
        for item in items:
            # Extrait les infos de l'item (structure basée sur celle passée par ChatService)
            variant_details = item.get('variant_details', {})
            sku = item.get('variant_sku', 'N/A')
            description = variant_details.get('name', 'Article inconnu')
            quantity = item.get('quantity', 0)
            unit_price = Decimal(item.get('price_at_quote', 0))
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
        
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
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

        # --- Fonction pour le Footer --- 
        def add_footer(canvas, doc):
            canvas.saveState()
            footer = Paragraph(FOOTER_TEXT, footer_style)
            w, h = footer.wrap(doc.width, doc.bottomMargin)
            footer.drawOn(canvas, doc.leftMargin, h)
            canvas.restoreState()

        # --- Génération du PDF dans le buffer --- 
        try:
            doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            logger.info(f"[PDFGen] PDF devis #{quote_id} généré en mémoire ({len(pdf_bytes)} bytes).")
            
            # Sauvegarder si output_path est fourni
            if output_path:
                try:
                    # Créer le dossier parent si nécessaire
                    output_dir = os.path.dirname(output_path)
                    if output_dir:
                        os.makedirs(output_dir, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(pdf_bytes)
                    logger.info(f"[PDFGen] PDF devis #{quote_id} sauvegardé dans: {output_path}")
                except Exception as save_err:
                    logger.error(f"[PDFGen] Erreur sauvegarde PDF dans {output_path}: {save_err}", exc_info=True)
                    # Ne pas lever d'exception bloquante ici? La génération en mémoire a réussi.
                    pass
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"[PDFGen] Erreur ReportLab build() pour devis #{quote_id}: {e}", exc_info=True)
            raise PDFGenerationException(f"Erreur lors de la construction du PDF: {e}", original_exception=e) 