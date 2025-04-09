"""Exceptions spécifiques au domaine Address."""
from typing import Optional

class AddressDomainException(Exception):
    """Classe de base pour les exceptions du domaine Address."""
    pass

class AddressNotFoundException(AddressDomainException):
    """Levée lorsqu'une adresse spécifique n'est pas trouvée."""
    def __init__(self, address_id: Optional[int] = None, user_id: Optional[int] = None):
        if address_id:
            super().__init__(f"Adresse avec ID {address_id} non trouvée.")
            self.address_id = address_id
        elif user_id:
            super().__init__(f"Aucune adresse trouvée pour l'utilisateur ID {user_id}.")
            self.user_id = user_id
        else:
            super().__init__("Adresse non trouvée.")

class AddressOperationForbiddenException(AddressDomainException):
    """Levée lorsqu'une opération sur une adresse est interdite (ex: modifier l'adresse d'un autre utilisateur)."""
    def __init__(self, address_id: int, user_id: int, reason: str = "Opération non autorisée."):
        super().__init__(f"Opération interdite sur l'adresse ID {address_id} pour l'utilisateur ID {user_id}: {reason}")
        self.address_id = address_id
        self.user_id = user_id
        self.reason = reason

class CannotDeleteDefaultAddressException(AddressDomainException):
    """Levée lorsqu'on tente de supprimer l'adresse par défaut alors qu'il en existe d'autres."""
    def __init__(self, address_id: int, user_id: int):
        super().__init__(f"Impossible de supprimer l'adresse par défaut (ID: {address_id}) pour l'utilisateur ID {user_id} car d'autres adresses existent.")
        self.address_id = address_id
        self.user_id = user_id 