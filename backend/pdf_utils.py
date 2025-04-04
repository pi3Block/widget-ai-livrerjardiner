import logging
import os
from datetime import datetime
from decimal import Decimal
import models

# Imports ReportLab nécessaires pour la génération PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

logger = logging.getLogger(__name__)

def generate_quote_pdf(quote: models.QuoteDB) -> str:
    """Génère un fichier PDF de devis à partir d'un objet QuoteDB."""
    quote_id = quote.id
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
        bold_style = ParagraphStyle(name="Bold", parent=normal_style, fontName='Helvetica-Bold')

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
        elements.append(Paragraph(f"Date : {quote.quote_date.strftime('%d/%m/%Y')}", normal_style))
        elements.append(Spacer(1, 0.1*inch))

        if quote.user:
            user_name = quote.user.name if quote.user.name else "Client"
            user_email = quote.user.email
            elements.append(Paragraph(f"<b>Client :</b> {user_name} ({user_email})", normal_style))
            elements.append(Spacer(1, 0.2*inch))
        else:
             logger.warning(f"[PDF] Informations utilisateur non chargées pour devis {quote_id}")

        data = [
            [
                Paragraph("<b>Référence (SKU)</b>", normal_style), 
                Paragraph("<b>Description</b>", normal_style),
                Paragraph("<b>Quantité</b>", normal_style), 
                Paragraph("<b>Prix Unitaire (€)</b>", normal_style), 
                Paragraph("<b>Total Ligne (€)</b>", normal_style)
            ]
        ]
        
        grand_total = Decimal(0)
        
        for item in quote.items:
            sku = item.variant.sku if item.variant else "N/A"
            description = item.variant.product.name if item.variant and item.variant.product else "" 
            quantity = item.quantity
            unit_price = item.price_at_quote
            line_total = quantity * unit_price
            grand_total += line_total
            
            data.append([
                Paragraph(sku, normal_style),
                Paragraph(description, normal_style),
                str(quantity),
                f"{unit_price:.2f}",
                f"{line_total:.2f}"
            ])

        data.append([
            Paragraph(" ", normal_style),
            Paragraph(" ", normal_style),
            Paragraph(" ", normal_style),
            Paragraph("<b>Total Devis (€)</b>", bold_style),
            Paragraph(f"<b>{grand_total:.2f}</b>", bold_style)
        ])
        
        table = Table(data, colWidths=[1.5*inch, 2.5*inch, 0.8*inch, 1.2*inch, 1.5*inch])
        
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5a9a1f")),
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
