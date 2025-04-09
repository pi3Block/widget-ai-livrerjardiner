import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional, Dict, Any

# Import de la configuration
from src.email.config import settings
# Import des exceptions spécifiques
from src.email.exceptions import EmailSendingException, EmailConfigurationException
# Import de l'interface domaine
from src.email.sender import AbstractEmailSender

logger = logging.getLogger(__name__)

class SmtpEmailSender(AbstractEmailSender):
    """Implémentation de l'envoi d'email via SMTP standard."""

    def __init__(self,
                 smtp_host: str = settings.SMTP_HOST,
                 smtp_port: int = settings.SMTP_PORT,
                 smtp_user: Optional[str] = settings.SENDER_EMAIL,
                 smtp_password: Optional[str] = settings.SENDER_PASSWORD,
                 default_sender: Optional[str] = settings.SENDER_EMAIL,
                 use_tls: bool = settings.USE_TLS):
        
        if not all([smtp_host, smtp_port, smtp_user, smtp_password, default_sender]):
            logger.error("[SmtpEmailSender] Configuration SMTP incomplète.")
            raise EmailConfigurationException("Configuration SMTP (host, port, user, password, sender) incomplète.")

        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.default_sender = default_sender
        self.use_tls = use_tls
        logger.info(f"[SmtpEmailSender] Initialisé pour {smtp_host}:{smtp_port}")

    async def send_email(
        self,
        recipient_email: str,
        subject: str,
        html_content: str,
        sender_email: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        
        final_sender = sender_email or self.default_sender
        if not final_sender:
             logger.error("[SmtpEmailSender] Aucun email expéditeur défini (ni par défaut, ni spécifique).")
             return False

        msg = MIMEMultipart('related')
        msg["From"] = f"{settings.DEFAULT_FROM_NAME} <{final_sender}>"
        msg["To"] = recipient_email
        msg["Subject"] = subject
        
        # Contenu HTML
        msg.attach(MIMEText(html_content, "html"))

        # Pièces jointes
        if attachments:
            for attachment in attachments:
                filename = attachment.get('filename')
                content = attachment.get('content')
                subtype = attachment.get('subtype', 'octet-stream')
                if filename and content:
                    try:
                        part = MIMEApplication(content, _subtype=subtype)
                        part.add_header("Content-Disposition", "attachment", filename=filename)
                        msg.attach(part)
                        logger.debug(f"[SmtpEmailSender] Pièce jointe '{filename}' ajoutée.")
                    except Exception as e:
                         logger.error(f"[SmtpEmailSender] Erreur attachement '{filename}': {e}", exc_info=True)
                         pass 
                else:
                     logger.warning(f"[SmtpEmailSender] Pièce jointe ignorée (manque filename ou content): {attachment}")

        try:
            logger.debug(f"[SmtpEmailSender] Connexion à {self.smtp_host}:{self.smtp_port}")
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                 server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            
            server.set_debuglevel(0)
            logger.debug(f"[SmtpEmailSender] Authentification avec {self.smtp_user}")
            server.login(self.smtp_user, self.smtp_password)
            
            logger.info(f"[SmtpEmailSender] Envoi de l'email à {recipient_email} (Sujet: {subject})")
            server.sendmail(final_sender, [recipient_email], msg.as_string())
            logger.info(f"[SmtpEmailSender] Email envoyé avec succès à {recipient_email}")
            server.quit()
            return True
        
        except smtplib.SMTPAuthenticationError as e:
             logger.error(f"[SmtpEmailSender] Échec authentification SMTP: {e}", exc_info=True)
             raise EmailSendingException("Échec authentification SMTP.", original_exception=e)
        except smtplib.SMTPRecipientsRefused as e:
             logger.error(f"[SmtpEmailSender] Destinataire refusé: {recipient_email}. Détails: {e.recipients}", exc_info=True)
             return False 
        except smtplib.SMTPSenderRefused as e:
             logger.error(f"[SmtpEmailSender] Expéditeur refusé: {final_sender}. Détails: {e.sender}", exc_info=True)
             raise EmailSendingException(f"Expéditeur refusé par le serveur: {final_sender}", original_exception=e)
        except smtplib.SMTPException as e:
             logger.error(f"[SmtpEmailSender] Erreur SMTP générale lors de l'envoi à {recipient_email}: {e}", exc_info=True)
             raise EmailSendingException(f"Erreur SMTP: {e}", original_exception=e)
        except Exception as e:
            logger.error(f"[SmtpEmailSender] Erreur inattendue lors de l'envoi à {recipient_email}: {e}", exc_info=True)
            raise EmailSendingException(f"Erreur inattendue: {e}", original_exception=e) 