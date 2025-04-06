from typing import Optional
from datetime import datetime
import uuid # Pourrait être utilisé pour un ID de domaine unique si différent de l'ID DB

class UserEntity:
    """Représente un utilisateur dans le domaine métier."""

    def __init__(
        self,
        id: int, # Utilise l'ID de la DB pour l'instant, pourrait être un UUID
        email: str,
        name: Optional[str],
        is_admin: bool,
        hashed_password: str, # Garde le hash ici, la logique de hashage sera dans l'application
        created_at: datetime,
        updated_at: datetime,
        # Potentiellement d'autres attributs ou méthodes métier...
    ):
        self.id = id
        self.email = email
        self.name = name
        self.is_admin = is_admin
        self.hashed_password = hashed_password # Important pour la logique d'authentification
        self.created_at = created_at
        self.updated_at = updated_at

    # Exemple de méthode métier simple (si nécessaire)
    def is_administrator(self) -> bool:
        return self.is_admin

    # On pourrait ajouter des méthodes pour vérifier le mot de passe,
    # mais il est souvent préférable de garder cela dans un service applicatif
    # pour ne pas lier l'entité à une lib de hashage spécifique.

    # Note: Pas de relations directes ici. Les relations sont gérées
    # par les services applicatifs ou les dépôts si nécessaire.
