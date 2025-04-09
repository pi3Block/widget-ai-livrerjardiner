from typing import Annotated
from fastapi import Depends

# Domain
from email.sender import AbstractEmailSender

# Infrastructure
from email.smtp_sender import SmtpEmailSender

# Application
from email.services import EmailService

# --- Email Sender Dependency ---

def get_email_sender() -> AbstractEmailSender:
    """
    Fournit une instance de l'implémentation concrète de l'Email Sender.
    
    Actuellement, utilise SmtpEmailSender qui lit la configuration depuis `config.py`.
    Pourrait être adapté pour lire depuis des variables d'env ou un autre système.
    
    Returns:
        AbstractEmailSender: Instance de l'implémentation du sender d'emails
    """
    # SmtpEmailSender lève EmailConfigurationException si config manque
    return SmtpEmailSender()

EmailSenderDep = Annotated[AbstractEmailSender, Depends(get_email_sender)]

# --- Email Service Dependency ---

def get_email_service(
    email_sender: EmailSenderDep
) -> EmailService:
    """
    Fournit une instance du service d'envoi d'emails.
    
    Args:
        email_sender: Instance de l'implémentation du sender d'emails
        
    Returns:
        EmailService: Instance du service d'envoi d'emails
    """
    return EmailService(email_sender=email_sender)

EmailServiceDep = Annotated[EmailService, Depends(get_email_service)] 