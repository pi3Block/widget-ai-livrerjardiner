import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import jinja2 # Pour le templating HTML
from datetime import datetime
from decimal import Decimal

# Domain
from email.sender import AbstractEmailSender
from email.exceptions import EmailSendingException

# Application (pour les types si besoin, ex: OrderResponse pour formater l'email)
# Note: Éviter dépendances fortes Application <-> Application si possible.
# Ici, on pourrait passer des Dict simples formatés par le service appelant.
# from src.orders.application.schemas import OrderResponse 
# from src.quotes.application.schemas import QuoteResponse

logger = logging.getLogger(__name__)

# Configuration du moteur de templates Jinja2
# Chemin vers le dossier des templates
TEMPLATE_DIR = Path(__file__).parent / "templates"
if not TEMPLATE_DIR.is_dir():
    logger.warning(f"Le dossier de templates email n'existe pas: {TEMPLATE_DIR}")
    # Créer le dossier ?
    try:
        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
         logger.error(f"Impossible de créer le dossier de templates: {e}")

env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)), autoescape=jinja2.select_autoescape(['html', 'xml']))

class EmailService:
    """Service applicatif pour l'envoi d'emails métier."""

    def __init__(self, email_sender: AbstractEmailSender):
        self.email_sender = email_sender
        logger.info("[EmailService] Initialisé.")

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Charge et rend un template Jinja2."""
        try:
            template = env.get_template(template_name)
            return template.render(context)
        except jinja2.TemplateNotFound:
            logger.error(f"[EmailService] Template email non trouvé: {template_name} dans {TEMPLATE_DIR}")
            # Retourner un contenu par défaut ou lever une exception?
            return f"Erreur: Template '{template_name}' non trouvé."
        except Exception as e:
            logger.error(f"[EmailService] Erreur rendu template {template_name}: {e}", exc_info=True)
            return f"Erreur lors du rendu du template {template_name}."

    async def send_quote_details_email(
        self,
        recipient_email: str,
        quote_details: Dict[str, Any], # Attends un dict avec clés: id, user_name, total_amount, items etc.
        pdf_content: Optional[bytes] = None,
        pdf_filename: Optional[str] = None
    ) -> bool:
        """Envoie un email avec les détails du devis et le PDF en pièce jointe."""
        subject = f"Votre Devis #{quote_details.get('id', '')} - LivrerJardiner.fr"
        logger.info(f"[EmailService] Préparation email devis #{quote_details.get('id')} pour {recipient_email}")
        
        context = {
            "quote": quote_details,
            "user_name": quote_details.get('user_name', 'Client') # Fournir un nom par défaut
            # Ajouter d'autres variables nécessaires au template
        }
        html_content = self._render_template("quote_email.html", context)
        
        attachments = []
        if pdf_content and pdf_filename:
            attachments.append({
                "filename": pdf_filename,
                "content": pdf_content,
                "subtype": "pdf"
            })
        
        try:
            success = await self.email_sender.send_email(
                recipient_email=recipient_email,
                subject=subject,
                html_content=html_content,
                attachments=attachments
            )
            if success:
                 logger.info(f"[EmailService] Email devis #{quote_details.get('id')} envoyé à {recipient_email}")
            else:
                 logger.warning(f"[EmailService] L'envoi de l'email devis #{quote_details.get('id')} a échoué (retour sender: False) pour {recipient_email}")
            return success
        except EmailSendingException as e:
            logger.error(f"[EmailService] Erreur lors de l'envoi email devis #{quote_details.get('id')} à {recipient_email}: {e}", exc_info=True)
            return False
            
    async def send_order_confirmation_email(
        self,
        recipient_email: str,
        order_id: int,
        order_date: datetime,
        total_price: Decimal,
        items: List[Dict[str, Any]] # Liste de dicts avec sku, name, quantity, price
    ) -> bool:
        """Envoie un email de confirmation de commande."""
        subject = f"Confirmation de votre commande #{order_id} - LivrerJardiner.fr"
        logger.info(f"[EmailService] Préparation email confirmation commande #{order_id} pour {recipient_email}")
        
        # Formatter les données pour le template
        context = {
            "order_id": order_id,
            "order_date": order_date.strftime("%d/%m/%Y %H:%M") if order_date else "N/A",
            "total_price": f"{total_price:.2f}", # Formater le prix
            "items": items,
            # Ajouter d'autres infos si nécessaire (adresse livraison?)
        }
        html_content = self._render_template("order_confirmation_email.html", context)
        
        # Pas d'attachements pour la confirmation simple
        attachments = [] 
        
        try:
            success = await self.email_sender.send_email(
                recipient_email=recipient_email,
                subject=subject,
                html_content=html_content,
                attachments=attachments
            )
            if success:
                 logger.info(f"[EmailService] Email confirmation commande #{order_id} envoyé à {recipient_email}")
            else:
                 logger.warning(f"[EmailService] L'envoi email confirmation commande #{order_id} a échoué (retour sender: False) pour {recipient_email}")
            return success
        except EmailSendingException as e:
            logger.error(f"[EmailService] Erreur lors de l'envoi email confirmation commande #{order_id} à {recipient_email}: {e}", exc_info=True)
            return False

    async def send_status_update_email(
        self,
        recipient_email: str,
        order_id: int,
        new_status: str,
        order_date: datetime # Ou une autre date pertinente?
    ) -> bool:
        """Envoie une notification de mise à jour du statut de la commande."""
        subject = f"Mise à jour du statut de votre commande #{order_id} - LivrerJardiner.fr"
        logger.info(f"[EmailService] Préparation email MAJ statut commande #{order_id} ({new_status}) pour {recipient_email}")
        
        # Formatter les données pour le template
        context = {
            "order_id": order_id,
            "order_date": order_date.strftime("%d/%m/%Y") if order_date else "N/A",
            "new_status": new_status.capitalize(), # Mettre une majuscule pour affichage
            # Ajouter lien de suivi? Infos supplémentaires?
        }
        html_content = self._render_template("order_status_update_email.html", context)
        
        attachments = [] 
        
        try:
            success = await self.email_sender.send_email(
                recipient_email=recipient_email,
                subject=subject,
                html_content=html_content,
                attachments=attachments
            )
            if success:
                 logger.info(f"[EmailService] Email MAJ statut commande #{order_id} ({new_status}) envoyé à {recipient_email}")
            else:
                 logger.warning(f"[EmailService] L'envoi email MAJ statut commande #{order_id} a échoué (retour sender: False) pour {recipient_email}")
            return success
        except EmailSendingException as e:
            logger.error(f"[EmailService] Erreur lors de l'envoi email MAJ statut commande #{order_id} à {recipient_email}: {e}", exc_info=True)
            return False

    # Ajouter d'autres méthodes pour d'autres types d'emails (ex: reset password, bienvenue, etc.) 