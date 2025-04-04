import logging
import os
from datetime import datetime

# Imports ReportLab nécessaires pour la génération PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

logger = logging.getLogger(__name__)

def generate_quote_pdf(item: str, quantity: int, unit_price: float, total_price: float, quote_id: int) -> str:
    """Génère un fichier PDF de devis."""
    logger.debug(f"[PDF] Génération du PDF pour le devis #{quote_id}")
    pdf_path = f"quotes/quote_{quote_id}.pdf"
    try:
        os.makedirs("quotes", exist_ok=True)
        logger.debug(f"[PDF] Dossier quotes créé ou existant")

        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        title_style = styles["Heading1"]
        title_style.textColor = colors.HexColor("#5a9a1f")
        normal_style = styles["Normal"]
        normal_style.textColor = colors.black
        footer_style = ParagraphStyle(name="Footer", fontSize=10, textColor=colors.gray, alignment=1)

        logo_path = "static/logo.png"
        try:
             if os.path.exists(logo_path):
                logo = Image(logo_path, width=1.5*inch, height=0.75*inch)
                logo.hAlign = 'LEFT'
                elements.append(logo)
             else:
                logger.warning(f"[PDF] Logo non trouvé : {logo_path}")
                elements.append(Paragraph("LivrerJardiner.fr", title_style))
        except Exception as img_err:
            logger.error(f"[PDF] Erreur logo: {img_err}. Utilisation titre.")
            elements.append(Paragraph("LivrerJardiner.fr", title_style))

        elements.append(Spacer(1, 0.1*inch))

        # Informations de l'entreprise - Remplacer par les vraies infos si nécessaire
        company_info_text = (
            "<b>LivrerJardiner.fr</b><br/>"
            "123 Rue des Jardins, 75000 Paris<br/>"
            "Email : contact@livrerjardiner.fr<br/>"
            "Tél : +33 1 23 45 67 89"
        )
        company_info_style = ParagraphStyle(name='CompanyInfo', parent=normal_style, alignment=2)
        company_info = Paragraph(company_info_text, company_info_style)
        elements.append(company_info)
        elements.append(Spacer(1, 0.2*inch))

        elements.append(Paragraph(f"Devis #{quote_id}", styles["h2"]))
        elements.append(Paragraph(f"Date : {datetime.now().strftime('%d/%m/%Y')}", normal_style))
        elements.append(Spacer(1, 0.3*inch))

        data = [
            ["Article", "Quantité", "Prix unitaire (€)", "Total (€)"],
            [Paragraph(item, normal_style), str(quantity), f"{unit_price:.2f}", f"{total_price:.2f}"]
        ]
        table = Table(data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5a9a1f")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 1, colors.darkgrey),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F0F0F0")), 
            # ... autres styles table ... 
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.5*inch))

        elements.append(Paragraph(
            "Merci de valider ce devis pour confirmer votre commande.<br/>"
            "Pour toute question, contactez-nous à contact@livrerjardiner.fr.", 
            normal_style
        ))

        def add_footer(canvas, doc):
            canvas.saveState()
            footer = Paragraph("LivrerJardiner.fr - Votre partenaire pour un jardin fleuri", footer_style)
            w, h = footer.wrap(doc.width, doc.bottomMargin)
            footer.drawOn(canvas, doc.leftMargin, h)
            canvas.restoreState()

        doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
        logger.debug(f"[PDF] PDF généré : {pdf_path}")
        return pdf_path
    except Exception as e:
        logger.error(f"[PDF] Erreur génération PDF : {str(e)}", exc_info=True)
        raise
