from typing import Annotated
from fastapi import Depends

# Domain
from src.email.domain.sender import AbstractEmailSender

# Infrastructure
from src.email.infrastructure.smtp_sender import SmtpEmailSender

# Application
from src.email.application.services import EmailService

# --- Email Sender Dependency ---

def get_email_sender() -> AbstractEmailSender:
    """Fournit une instance de l'implémentation concrète de l'Email Sender.
    
    Actuellement, utilise SmtpEmailSender qui lit la configuration depuis `config.py`.
    Pourrait être adapté pour lire depuis des variables d'env ou un autre système.
    """
    # SmtpEmailSender lève EmailConfigurationException si config manque
    return SmtpEmailSender()

EmailSenderDep = Annotated[AbstractEmailSender, Depends(get_email_sender)]

# --- Email Service Dependency ---

def get_email_service(
    email_sender: EmailSenderDep
) -> EmailService:
    """Injecte l'Email Sender et fournit une instance de EmailService."""
    return EmailService(email_sender=email_sender)

EmailServiceDep = Annotated[EmailService, Depends(get_email_service)] 