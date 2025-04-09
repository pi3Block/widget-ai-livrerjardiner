from datetime import datetime
from pathlib import Path
from src.pdf.templates import PDFTemplateManager

def generate_sample_invoice():
    # Initialiser le gestionnaire de templates
    template_manager = PDFTemplateManager()
    
    # Données de l'entreprise
    company_data = {
        "name": "Livrer & Jardiner",
        "address": "123 Rue du Commerce, 75001 Paris",
        "phone": "+33 1 23 45 67 89",
        "email": "contact@livrerjardiner.fr",
        "siret": "123 456 789 00001"
    }
    
    # Données du client
    client_data = {
        "name": "Jean Dupont",
        "address": "456 Avenue des Fleurs, 69001 Lyon",
        "phone": "+33 4 56 78 90 12",
        "email": "jean.dupont@email.com"
    }
    
    # Articles de la facture
    items = [
        {
            "description": "Service de livraison - Zone A",
            "quantity": 1,
            "unit_price": 29.99,
            "total": 29.99
        },
        {
            "description": "Service de jardinage - 2 heures",
            "quantity": 1,
            "unit_price": 45.00,
            "total": 45.00
        }
    ]
    
    # Calculer le total
    total_amount = sum(item["total"] for item in items)
    
    # Préparer les données pour le template
    template_data = {
        "company": company_data,
        "client": client_data,
        "invoice_number": f"INV-{datetime.now().strftime('%Y%m%d')}-001",
        "invoice_date": datetime.now().strftime("%d/%m/%Y"),
        "items": items,
        "total_amount": total_amount
    }
    
    # Générer le PDF
    output_dir = Path("output/invoices")
    output_path = template_manager.generate_pdf(
        template_name="invoice.html",
        data=template_data,
        output_dir=output_dir,
        filename=f"facture_{template_data['invoice_number']}.pdf"
    )
    
    print(f"Facture générée avec succès: {output_path}")

if __name__ == "__main__":
    generate_sample_invoice() 