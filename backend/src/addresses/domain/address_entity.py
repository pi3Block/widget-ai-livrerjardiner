from typing import Optional
from datetime import datetime

class AddressEntity:
    """Représente une adresse dans le domaine métier."""

    def __init__(
        self,
        id: int,
        user_id: int, # Garde la référence à l'utilisateur
        street: str,
        city: str,
        zip_code: str,
        country: str,
        is_default: bool,
        created_at: datetime,
        updated_at: datetime,
    ):
        self.id = id
        self.user_id = user_id
        self.street = street
        self.city = city
        self.zip_code = zip_code
        self.country = country
        self.is_default = is_default
        self.created_at = created_at
        self.updated_at = updated_at

    # Potentiellement des méthodes métier liées à une adresse
    # def format_address(self) -> str:
    #    return f"{self.street}, {self.zip_code} {self.city}, {self.country}" 