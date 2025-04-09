"""
Configuration spécifique au module Orders.
Contient les constantes et paramètres de configuration pour le module de gestion des commandes.
"""

from typing import List, Dict
from decimal import Decimal

# Statuts autorisés pour une commande
ALLOWED_ORDER_STATUS: List[str] = [
    "pending",      # Commande en attente de traitement
    "processing",   # Commande en cours de traitement
    "shipped",      # Commande expédiée
    "delivered",    # Commande livrée
    "cancelled"     # Commande annulée
]

# Mapping des statuts pour l'affichage en français
ORDER_STATUS_DISPLAY: Dict[str, str] = {
    "pending": "En attente",
    "processing": "En traitement",
    "shipped": "Expédiée",
    "delivered": "Livrée",
    "cancelled": "Annulée"
}

# Configuration des limites
MAX_ITEMS_PER_ORDER: int = 50  # Nombre maximum d'articles par commande
MIN_ORDER_AMOUNT: Decimal = Decimal("0.01")  # Montant minimum d'une commande
MAX_ORDER_AMOUNT: Decimal = Decimal("99999.99")  # Montant maximum d'une commande

# Configuration de la pagination
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

# Configuration des délais (en heures)
CANCELLATION_WINDOW: int = 24  # Délai d'annulation après création
MODIFICATION_WINDOW: int = 1   # Délai de modification après création 