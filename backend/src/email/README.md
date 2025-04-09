# Module Email

## Description
Module de gestion des emails pour l'application LivrerJardiner. Ce module fournit une interface abstraite pour l'envoi d'emails avec une implémentation SMTP par défaut.

## Architecture
Le module suit une architecture en couches :
- **Domain** : Interfaces et exceptions (`sender.py`, `exceptions.py`)
- **Infrastructure** : Implémentation SMTP (`smtp_sender.py`)
- **Application** : Services métier (`services.py`)
- **Configuration** : Paramètres (`config.py`)
- **Validation** : Schémas Pydantic (`models.py`)

## Configuration
Les variables d'environnement requises sont :
```env
EMAIL_SMTP_HOST=smtp.example.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER_EMAIL=noreply@livrerjardiner.fr
EMAIL_SENDER_PASSWORD=your_password
EMAIL_USE_TLS=true
EMAIL_DEFAULT_FROM_NAME=LivrerJardiner
```

## Utilisation

### Injection de dépendances
```python
from email.dependencies import EmailServiceDep

@router.post("/send-email")
async def send_email(email_service: EmailServiceDep):
    await email_service.send_quote_details_email(...)
```

### Envoi d'un email de devis
```python
from email.models import QuoteEmailRequest

quote_request = QuoteEmailRequest(
    recipient_email="client@example.com",
    subject="Votre devis",
    html_content="<h1>Votre devis</h1>...",
    quote_id="123",
    user_name="John Doe",
    total_amount=99.99,
    items=[{"name": "Produit 1", "price": 49.99}]
)

await email_service.send_quote_details_email(
    recipient_email=quote_request.recipient_email,
    quote_details=quote_request.dict(),
    pdf_content=b"...",  # Optionnel
    pdf_filename="devis.pdf"  # Optionnel
)
```

### Envoi d'une confirmation de commande
```python
from email.models import OrderConfirmationEmailRequest

order_request = OrderConfirmationEmailRequest(
    recipient_email="client@example.com",
    subject="Confirmation de commande",
    html_content="<h1>Confirmation</h1>...",
    order_id=123,
    order_date=datetime.now(),
    total_price=149.99,
    items=[{"name": "Produit 1", "quantity": 2, "price": 49.99}]
)

await email_service.send_order_confirmation_email(
    recipient_email=order_request.recipient_email,
    order_id=order_request.order_id,
    order_date=order_request.order_date,
    total_price=order_request.total_price,
    items=order_request.items
)
```

## Templates
Les templates HTML sont stockés dans le dossier `templates/`. Chaque type d'email a son propre template :
- `quote_email.html` : Template pour les emails de devis
- `order_confirmation_email.html` : Template pour les confirmations de commande
- `order_status_update_email.html` : Template pour les mises à jour de statut

## Tests
Les tests sont organisés dans le dossier `tests/email/` :
- `test_smtp_sender.py` : Tests de l'implémentation SMTP
- `test_services.py` : Tests des services métier
- `test_dependencies.py` : Tests des dépendances FastAPI

## Extensions
Pour ajouter une nouvelle implémentation d'envoi d'email (ex: SendGrid, Mailgun) :
1. Créer une nouvelle classe implémentant `AbstractEmailSender`
2. Ajouter la configuration nécessaire dans `config.py`
3. Mettre à jour les dépendances dans `dependencies.py` 