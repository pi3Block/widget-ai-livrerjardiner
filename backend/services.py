import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication


import config # Pour les configurations SMTP
import models # Ajout de l'import manquant

# Importer la classe SMTP depuis utils
from utils import SMTPHostinger

logger = logging.getLogger(__name__)

def send_quote_email(user_email: str, quote_id: int, pdf_path: str) -> bool:
    """Crée et envoie un email avec le devis PDF en pièce jointe."""
    logger.debug(f"[SERVICE] Préparation de l'email à {user_email} pour le devis #{quote_id}")
    subject = f"Devis #{quote_id} - LivrerJardiner.fr"
    body = f"""
    Bonjour,

    Voici votre devis #{quote_id} pour votre commande. Veuillez le valider pour confirmer.

    Merci de votre confiance,
    L'équipe LivrerJardiner.fr
    """

    msg = MIMEMultipart()
    msg["From"] = config.SENDER_EMAIL
    msg["To"] = user_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        # Vérifier si le fichier PDF existe avant de tenter de l'ouvrir
        if not os.path.exists(pdf_path):
            logger.error(f"[SERVICE] Le fichier PDF n'existe pas pour l'attachement : {pdf_path}")
            return False
        
        with open(pdf_path, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
            attach.add_header("Content-Disposition", "attachment", filename=f"devis_{quote_id}.pdf")
            msg.attach(attach)
        logger.debug(f"[SERVICE] Fichier PDF {pdf_path} attaché à l'email.")

    except Exception as e:
        logger.error(f"[SERVICE] Erreur lors de la lecture ou attachement du PDF ({pdf_path}) : {str(e)}", exc_info=True)
        return False

    # Créer, authentifier, envoyer et fermer la connexion pour cet email
    local_smtp_client = SMTPHostinger()
    email_sent = False
    try:
        logger.debug(f"[SERVICE] Tentative d'authentification SMTP ({config.SMTP_HOST}:{config.SMTP_PORT}) pour {user_email}")
        if local_smtp_client.auth(config.SENDER_EMAIL, config.SENDER_PASSWORD, config.SMTP_HOST, config.SMTP_PORT, debug=True):
            logger.debug(f"[SERVICE] Auth réussie. Tentative d'envoi à {user_email}")
            email_sent = local_smtp_client.send(
                recipient=user_email,
                sender=config.SENDER_EMAIL,
                subject=subject,
                message=msg.as_string()
            )
            if not email_sent:
                logger.error(f"[SERVICE] La méthode send a retourné False pour {user_email}")
        else:
            logger.error(f"[SERVICE] Échec de l'authentification SMTP lors de l'envoi à {user_email}")

    except Exception as e:
        logger.error(f"[SERVICE] Exception lors de l'envoi de l'email à {user_email}: {str(e)}", exc_info=True)
        email_sent = False
    finally:
        logger.debug(f"[SERVICE] Fermeture de la connexion SMTP pour {user_email}")
        local_smtp_client.close()

    if not email_sent:
        logger.error(f"[SERVICE] Échec final de l'envoi de l'email de devis à {user_email}")
    else:
        logger.info(f"[SERVICE] Email de devis envoyé avec succès à {user_email}")

    return email_sent

# --- Nouvelle fonction pour email de confirmation de commande ---
def send_order_confirmation_email(user_email: str, order: models.OrderDB) -> bool:
    """Crée et envoie un email de confirmation de commande simple."""
    logger.debug(f"[SERVICE] Préparation de l'email de confirmation à {user_email} pour la commande #{order.id}")
    subject = f"Confirmation de votre commande #{order.id} - LivrerJardiner.fr"
    # Construire un résumé simple de la commande
    item_summary = "\nRécapitulatif de votre commande:\n"
    for item in order.items:
        item_summary += f"- {item.quantity} x SKU {item.variant.sku if item.variant else '[inconnu]'} @ {item.price_at_order:.2f} €\n"
    item_summary += f"\nTotal: {order.total_amount:.2f} €\n"

    body = f"""
    Bonjour {order.user.name if order.user and order.user.name else ''},

    Merci pour votre commande #{order.id} !
    {item_summary}
    Elle sera expédiée à l'adresse suivante :
    {order.delivery_address.street if order.delivery_address else '[Adresse manquante]'}
    {order.delivery_address.zip_code if order.delivery_address else ''} {order.delivery_address.city if order.delivery_address else ''}

    Vous pouvez suivre son statut depuis votre compte.

    Merci de votre confiance,
    L'équipe LivrerJardiner.fr
    """

    msg = MIMEMultipart()
    msg["From"] = config.SENDER_EMAIL
    msg["To"] = user_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # TODO: Ajouter une pièce jointe PDF si nécessaire (comme pour le devis)

    # Créer, authentifier, envoyer et fermer la connexion pour cet email
    local_smtp_client = SMTPHostinger()
    email_sent = False
    try:
        logger.debug(f"[SERVICE] Tentative d'authentification SMTP ({config.SMTP_HOST}:{config.SMTP_PORT}) pour commande {order.id} à {user_email}")
        if local_smtp_client.auth(config.SENDER_EMAIL, config.SENDER_PASSWORD, config.SMTP_HOST, config.SMTP_PORT, debug=True):
            logger.debug(f"[SERVICE] Auth réussie. Tentative d'envoi confirmation commande à {user_email}")
            email_sent = local_smtp_client.send(
                recipient=user_email,
                sender=config.SENDER_EMAIL,
                subject=subject,
                message=msg.as_string()
            )
            if not email_sent:
                logger.error(f"[SERVICE] La méthode send a retourné False pour commande {order.id} à {user_email}")
        else:
            logger.error(f"[SERVICE] Échec de l'authentification SMTP lors de l'envoi commande {order.id} à {user_email}")

    except Exception as e:
        logger.error(f"[SERVICE] Exception lors de l'envoi email commande {order.id} à {user_email}: {str(e)}", exc_info=True)
        email_sent = False
    finally:
        logger.debug(f"[SERVICE] Fermeture de la connexion SMTP pour email commande {order.id} à {user_email}")
        local_smtp_client.close()

    if not email_sent:
        logger.error(f"[SERVICE] Échec final de l'envoi email confirmation commande {order.id} à {user_email}")
    else:
        logger.info(f"[SERVICE] Email confirmation commande {order.id} envoyé avec succès à {user_email}")

    return email_sent
