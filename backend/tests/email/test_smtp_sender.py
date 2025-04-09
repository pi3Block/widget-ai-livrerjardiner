import pytest
from unittest.mock import Mock, patch
from email.mime.multipart import MIMEMultipart
from email.smtp_sender import SmtpEmailSender
from email.exceptions import EmailSendingException, EmailConfigurationException
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

@pytest.fixture
def smtp_sender(mock_settings):
    """Fixture pour l'instance SmtpEmailSender."""
    with patch("email.smtp_sender.settings", mock_settings):
        return SmtpEmailSender()

def test_smtp_sender_initialization(mock_settings):
    """Test l'initialisation du SmtpEmailSender."""
    with patch("email.smtp_sender.settings", mock_settings):
        sender = SmtpEmailSender()
        assert sender.smtp_host == mock_settings.SMTP_HOST
        assert sender.smtp_port == mock_settings.SMTP_PORT
        assert sender.smtp_user == mock_settings.SENDER_EMAIL
        assert sender.smtp_password == mock_settings.SENDER_PASSWORD
        assert sender.use_tls == mock_settings.USE_TLS

def test_smtp_sender_initialization_missing_config():
    """Test que l'initialisation échoue si la configuration est incomplète."""
    with patch("email.smtp_sender.settings", EmailSettings(
        SMTP_HOST="",
        SMTP_PORT=587,
        SENDER_EMAIL="",
        SENDER_PASSWORD="test",
        USE_TLS=True
    )):
        with pytest.raises(EmailConfigurationException):
            SmtpEmailSender()

@pytest.mark.asyncio
async def test_send_email_success(smtp_sender):
    """Test l'envoi réussi d'un email."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        result = await smtp_sender.send_email(
            recipient_email="test@example.com",
            subject="Test Subject",
            html_content="<h1>Test</h1>"
        )
        
        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with(
            smtp_sender.smtp_user,
            smtp_sender.smtp_password
        )
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

@pytest.mark.asyncio
async def test_send_email_with_attachments(smtp_sender):
    """Test l'envoi d'un email avec pièces jointes."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        attachments = [{
            "filename": "test.pdf",
            "content": b"test content",
            "subtype": "pdf"
        }]
        
        result = await smtp_sender.send_email(
            recipient_email="test@example.com",
            subject="Test Subject",
            html_content="<h1>Test</h1>",
            attachments=attachments
        )
        
        assert result is True
        mock_server.sendmail.assert_called_once()
        
        # Vérifier que le message contient la pièce jointe
        call_args = mock_server.sendmail.call_args[0]
        message = call_args[2]
        assert isinstance(message, str)
        assert "test.pdf" in message
        assert "application/pdf" in message

@pytest.mark.asyncio
async def test_send_email_authentication_error(smtp_sender):
    """Test la gestion des erreurs d'authentification."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        mock_server.login.side_effect = Exception("Authentication failed")
        
        with pytest.raises(EmailSendingException):
            await smtp_sender.send_email(
                recipient_email="test@example.com",
                subject="Test Subject",
                html_content="<h1>Test</h1>"
            ) 