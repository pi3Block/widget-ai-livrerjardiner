"""
Modèles et schémas pour le module email.

Ce module définit les modèles et schémas utilisés pour la validation des données
dans le module email, en suivant les règles d'architecture recommandées.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Schémas pour les pièces jointes ---
class EmailAttachment(BaseModel):
    """Schéma pour les pièces jointes d'email."""
    filename: str = Field(..., description="Nom du fichier")
    content: bytes = Field(..., description="Contenu binaire du fichier")
    subtype: str = Field(default="octet-stream", description="Type MIME du fichier")

# --- Schéma de base pour les requêtes d'email ---
class EmailRequest(BaseModel):
    """Schéma de base pour une requête d'envoi d'email."""
    recipient_email: EmailStr = Field(..., description="Adresse email du destinataire")
    subject: str = Field(..., description="Sujet de l'email")
    html_content: str = Field(..., description="Contenu HTML de l'email")
    sender_email: Optional[EmailStr] = Field(None, description="Adresse email de l'expéditeur (optionnel)")
    attachments: Optional[List[EmailAttachment]] = Field(default=None, description="Liste des pièces jointes")

# --- Schémas spécifiques pour différents types d'emails ---
class QuoteEmailRequest(EmailRequest):
    """Schéma spécifique pour l'envoi d'un email de devis."""
    quote_id: str = Field(..., description="Identifiant du devis")
    user_name: str = Field(..., description="Nom de l'utilisateur")
    total_amount: float = Field(..., description="Montant total du devis")
    items: List[Dict[str, Any]] = Field(..., description="Liste des articles du devis")

class OrderConfirmationEmailRequest(EmailRequest):
    """Schéma spécifique pour l'envoi d'un email de confirmation de commande."""
    order_id: int = Field(..., description="Identifiant de la commande")
    order_date: datetime = Field(..., description="Date de la commande")
    total_price: float = Field(..., description="Prix total de la commande")
    items: List[Dict[str, Any]] = Field(..., description="Liste des articles commandés")

class OrderStatusUpdateEmailRequest(EmailRequest):
    """Schéma spécifique pour l'envoi d'un email de mise à jour de statut de commande."""
    order_id: int = Field(..., description="Identifiant de la commande")
    new_status: str = Field(..., description="Nouveau statut de la commande")
    order_date: datetime = Field(..., description="Date de la commande") 