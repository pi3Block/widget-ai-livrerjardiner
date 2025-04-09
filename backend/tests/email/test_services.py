import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from decimal import Decimal
from email.services import EmailService
from email.schemas import QuoteEmailRequest, OrderConfirmationEmailRequest, OrderStatusUpdateEmailRequest
from email.exceptions import EmailSendingException

@pytest.fixture
def mock_email_sender():
    """Fixture pour un mock de l'email sender."""
    sender = AsyncMock()
    sender.send_email.return_value = True
    return sender

@pytest.fixture
def email_service(mock_email_sender):
    """Fixture pour l'instance EmailService."""
    return EmailService(email_sender=mock_email_sender)

@pytest.mark.asyncio
async def test_send_quote_details_email(email_service, mock_email_sender):
    """Test l'envoi d'un email de devis."""
    quote_request = QuoteEmailRequest(
        recipient_email="test@example.com",
        subject="Votre devis",
        html_content="<h1>Test</h1>",
        quote_id="123",
        user_name="John Doe",
        total_amount=99.99,
        items=[{"name": "Produit 1", "price": 49.99}]
    )
    
    result = await email_service.send_quote_details_email(
        recipient_email=quote_request.recipient_email,
        quote_details=quote_request.dict(),
        pdf_content=b"test pdf",
        pdf_filename="devis.pdf"
    )
    
    assert result is True
    mock_email_sender.send_email.assert_called_once()
    call_args = mock_email_sender.send_email.call_args[1]
    assert call_args["recipient_email"] == quote_request.recipient_email
    assert "devis" in call_args["subject"].lower()
    assert call_args["attachments"] is not None
    assert len(call_args["attachments"]) == 1
    assert call_args["attachments"][0]["filename"] == "devis.pdf"

@pytest.mark.asyncio
async def test_send_order_confirmation_email(email_service, mock_email_sender):
    """Test l'envoi d'un email de confirmation de commande."""
    order_request = OrderConfirmationEmailRequest(
        recipient_email="test@example.com",
        subject="Confirmation de commande",
        html_content="<h1>Test</h1>",
        order_id=123,
        order_date=datetime.now(),
        total_price=149.99,
        items=[{"name": "Produit 1", "quantity": 2, "price": 49.99}]
    )
    
    result = await email_service.send_order_confirmation_email(
        recipient_email=order_request.recipient_email,
        order_id=order_request.order_id,
        order_date=order_request.order_date,
        total_price=order_request.total_price,
        items=order_request.items
    )
    
    assert result is True
    mock_email_sender.send_email.assert_called_once()
    call_args = mock_email_sender.send_email.call_args[1]
    assert call_args["recipient_email"] == order_request.recipient_email
    assert "confirmation" in call_args["subject"].lower()
    assert str(order_request.order_id) in call_args["subject"]

@pytest.mark.asyncio
async def test_send_order_status_update_email(email_service, mock_email_sender):
    """Test l'envoi d'un email de mise à jour de statut."""
    status_request = OrderStatusUpdateEmailRequest(
        recipient_email="test@example.com",
        subject="Mise à jour de commande",
        html_content="<h1>Test</h1>",
        order_id=123,
        new_status="En cours de livraison",
        order_date=datetime.now()
    )
    
    result = await email_service.send_status_update_email(
        recipient_email=status_request.recipient_email,
        order_id=status_request.order_id,
        new_status=status_request.new_status,
        order_date=status_request.order_date
    )
    
    assert result is True
    mock_email_sender.send_email.assert_called_once()
    call_args = mock_email_sender.send_email.call_args[1]
    assert call_args["recipient_email"] == status_request.recipient_email
    assert "mise à jour" in call_args["subject"].lower()
    assert str(status_request.order_id) in call_args["subject"]

@pytest.mark.asyncio
async def test_send_email_error_handling(email_service, mock_email_sender):
    """Test la gestion des erreurs d'envoi d'email."""
    mock_email_sender.send_email.side_effect = EmailSendingException("Test error")
    
    result = await email_service.send_quote_details_email(
        recipient_email="test@example.com",
        quote_details={"id": "123"},
        pdf_content=None,
        pdf_filename=None
    )
    
    assert result is False
    mock_email_sender.send_email.assert_called_once()

@pytest.mark.asyncio
async def test_template_rendering(email_service, mock_email_sender):
    """Test le rendu des templates d'email."""
    quote_details = {
        "id": "123",
        "user_name": "John Doe",
        "total_amount": 99.99,
        "items": [{"name": "Produit 1", "price": 49.99}]
    }
    
    result = await email_service.send_quote_details_email(
        recipient_email="test@example.com",
        quote_details=quote_details,
        pdf_content=None,
        pdf_filename=None
    )
    
    assert result is True
    call_args = mock_email_sender.send_email.call_args[1]
    html_content = call_args["html_content"]
    assert "John Doe" in html_content
    assert "99.99" in html_content
    assert "Produit 1" in html_content 