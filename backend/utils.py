import logging
import smtplib
import ssl

logger = logging.getLogger(__name__)

class SMTPHostinger:
    """
    SMTP module for Hostinger emails
    """
    def __init__(self):
        self.conn = None

    def auth(self, user: str, password: str, host: str, port: int, debug: bool = False):
        """
        Authenticates a session
        """
        self.user = user
        self.password = password
        self.host = host
        self.port = port

        context = ssl.create_default_context()

        self.conn = smtplib.SMTP_SSL(host, port, context=context)
        self.conn.set_debuglevel(debug)

        try:
            self.conn.login(user, password)
            logger.debug("Connexion SMTP réussie")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Erreur d'authentification SMTP : {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la connexion SMTP : {str(e)}")
            return False

    def send(self, recipient: str, sender: str, subject: str, message: str):
        """
        Sends an email to the specified recipient.
        Assumes 'message' is a fully formatted email string (e.g., from msg.as_string()).
        The subject parameter is ignored here as it should be part of the message string.
        """
        if self.conn:
            try:
                # Envoyer directement la chaîne 'message' formatée
                # Assurer que le destinataire est une liste
                self.conn.sendmail(sender, [recipient], message)
                logger.debug(f"Email envoyé à {recipient}")
                return True
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'email : {str(e)}")
                return False
        else:
            logger.error("Connexion SMTP non établie")
            return False

    def close(self):
        """
        Closes the SMTP connection
        """
        if self.conn:
            try:
                self.conn.quit()
                logger.debug("Connexion SMTP fermée proprement via quit()")
            except smtplib.SMTPServerDisconnected:
                logger.warning("Tentative de fermeture (quit) sur une connexion SMTP déjà déconnectée.")
            except Exception as e:
                logger.error(f"Erreur inattendue lors de la fermeture SMTP (quit) : {str(e)}")
            finally:
                self.conn = None # Assurer que self.conn est None après tentative de fermeture
        else:
             logger.debug("Aucune connexion SMTP active à fermer.")
