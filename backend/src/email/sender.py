from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class AbstractEmailSender(ABC):
    """Interface abstraite pour un service d'envoi d'e-mails."""

    @abstractmethod
    async def send_email(
        self,
        recipient_email: str,
        subject: str,
        html_content: str,
        sender_email: Optional[str] = None, # Peut être défini globalement ou par email
        attachments: Optional[List[Dict[str, Any]]] = None # Ex: [{'filename': 'devis.pdf', 'content': b'...'}]
    ) -> bool:
        """Envoie un email.
        
        Args:
            recipient_email: Adresse email du destinataire.
            subject: Sujet de l'email.
            html_content: Contenu HTML de l'email.
            sender_email: Adresse email de l'expéditeur (si non configuré globalement).
            attachments: Liste optionnelle de pièces jointes.
            
        Returns:
            True si l'envoi a réussi (ou a été mis en file d'attente avec succès),
            False sinon.
            
        Raises:
            EmailSendingException: Si une erreur majeure empêche l'envoi.
        """
        raise NotImplementedError 