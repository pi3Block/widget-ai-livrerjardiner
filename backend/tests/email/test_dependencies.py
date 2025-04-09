import pytest
from fastapi import Depends
from email.dependencies import get_email_sender, get_email_service, EmailSenderDep, EmailServiceDep
from email.sender import AbstractEmailSender
from email.services import EmailService
from email.smtp_sender import SmtpEmailSender
from email.config import EmailSettings

@pytest.fixture
def mock_settings():
    """Fixture pour les paramètres de test."""
    return EmailSettings(
        SMTP_HOST="smtp.test.com",
        SMTP_PORT=587,
        SENDER_EMAIL="test@livrerjardiner.fr",
        SENDER_PASSWORD="test_password",
        USE_TLS=True
    )

def test_get_email_sender(mock_settings):
    """Test la fonction de dépendance get_email_sender."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("email.smtp_sender.settings", mock_settings)
        sender = get_email_sender()
        assert isinstance(sender, SmtpEmailSender)
        assert sender.smtp_host == mock_settings.SMTP_HOST
        assert sender.smtp_port == mock_settings.SMTP_PORT

def test_get_email_sender_missing_config():
    """Test que get_email_sender échoue si la configuration est incomplète."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("email.smtp_sender.settings", EmailSettings(
            SMTP_HOST="",
            SMTP_PORT=587,
            SENDER_EMAIL="",
            SENDER_PASSWORD="test",
            USE_TLS=True
        ))
        with pytest.raises(Exception):
            get_email_sender()

def test_get_email_service():
    """Test la fonction de dépendance get_email_service."""
    mock_sender = AbstractEmailSender()
    service = get_email_service(email_sender=mock_sender)
    assert isinstance(service, EmailService)
    assert service.email_sender == mock_sender

def test_email_sender_dependency_type():
    """Test le type de la dépendance EmailSenderDep."""
    assert isinstance(EmailSenderDep, type)
    assert issubclass(EmailSenderDep.__origin__, AbstractEmailSender)

def test_email_service_dependency_type():
    """Test le type de la dépendance EmailServiceDep."""
    assert isinstance(EmailServiceDep, type)
    assert issubclass(EmailServiceDep.__origin__, EmailService)

@pytest.mark.asyncio
async def test_dependency_injection_chain():
    """Test la chaîne complète d'injection de dépendances."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("email.smtp_sender.settings", EmailSettings(
            SMTP_HOST="smtp.test.com",
            SMTP_PORT=587,
            SENDER_EMAIL="test@livrerjardiner.fr",
            SENDER_PASSWORD="test_password",
            USE_TLS=True
        ))
        
        # Simuler l'injection de dépendances FastAPI
        sender = get_email_sender()
        service = get_email_service(email_sender=sender)
        
        assert isinstance(sender, SmtpEmailSender)
        assert isinstance(service, EmailService)
        assert service.email_sender == sender 