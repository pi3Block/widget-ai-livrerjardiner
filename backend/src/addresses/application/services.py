import logging
from typing import Optional, List

# Import de l'interface du dépôt et de l'entité
from src.addresses.domain.repositories import AbstractAddressRepository
from src.addresses.domain.address_entity import AddressEntity

# Import des schémas (si besoin de DTOs spécifiques)
# from . import schemas as app_schemas

# Import des exceptions
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class AddressService:
    """Service pour gérer la logique métier des adresses."""

    def __init__(self, address_repo: AbstractAddressRepository):
        self.address_repo = address_repo

    async def get_address_by_id(self, address_id: int, requesting_user_id: int) -> AddressEntity:
        """Récupère une adresse par ID, vérifiant l'appartenance à l'utilisateur."""
        logger.debug(f"[AddrService] Récupération adresse ID: {address_id} pour user {requesting_user_id}")
        address = await self.address_repo.get_by_id(address_id)
        if not address:
            raise HTTPException(status_code=404, detail="Adresse non trouvée.")
        if address.user_id != requesting_user_id:
            # Ne pas révéler si l'adresse existe mais appartient à qqn d'autre
            logger.warning(f"[AddrService] Tentative d'accès non autorisé à l'adresse {address_id} par user {requesting_user_id}")
            raise HTTPException(status_code=404, detail="Adresse non trouvée.") # Masquer comme 404
        return address

    async def list_user_addresses(self, user_id: int) -> List[AddressEntity]:
        """Liste les adresses d'un utilisateur."""
        logger.debug(f"[AddrService] Listage adresses pour user ID: {user_id}")
        return await self.address_repo.list_by_user_id(user_id)

    async def add_address_for_user(
        self,
        user_id: int,
        street: str,
        city: str,
        zip_code: str,
        country: str
    ) -> AddressEntity:
        """Ajoute une nouvelle adresse pour un utilisateur."""
        logger.debug(f"[AddrService] Ajout adresse pour user ID: {user_id}")
        # Construire l'entité (sans ID, created/updated)
        from datetime import datetime # Import local
        address_entity = AddressEntity(
            id=None,
            user_id=user_id,
            street=street,
            city=city,
            zip_code=zip_code,
            country=country,
            is_default=False, # Le dépôt gérera la logique de défaut
            created_at=datetime.now(), # Temporaire
            updated_at=datetime.now()  # Temporaire
        )
        return await self.address_repo.add(address_entity)

    async def update_user_address(
        self,
        address_id: int,
        requesting_user_id: int,
        street: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None,
        country: Optional[str] = None
    ) -> AddressEntity:
        """Met à jour une adresse pour un utilisateur."""
        logger.debug(f"[AddrService] MAJ adresse ID: {address_id} pour user {requesting_user_id}")
        # Récupérer l'adresse existante et vérifier la propriété
        existing_address = await self.get_address_by_id(address_id, requesting_user_id)
        
        # Créer une nouvelle entité avec les modifications
        updated_entity = AddressEntity(
            id=existing_address.id,
            user_id=existing_address.user_id,
            street=street if street is not None else existing_address.street,
            city=city if city is not None else existing_address.city,
            zip_code=zip_code if zip_code is not None else existing_address.zip_code,
            country=country if country is not None else existing_address.country,
            is_default=existing_address.is_default, # Ne pas modifier ici
            created_at=existing_address.created_at,
            updated_at=datetime.now() # Mettre à jour
        )

        updated_result = await self.address_repo.update(updated_entity)
        if not updated_result:
            # Ne devrait pas arriver si get_address_by_id a réussi, mais sécurité
            raise HTTPException(status_code=404, detail="Adresse non trouvée lors de la mise à jour.")
        return updated_result

    async def delete_user_address(self, address_id: int, requesting_user_id: int) -> bool:
        """Supprime une adresse pour un utilisateur."""
        logger.debug(f"[AddrService] Suppression adresse ID: {address_id} pour user {requesting_user_id}")
        # Vérifier la propriété avant de supprimer
        await self.get_address_by_id(address_id, requesting_user_id)
        # Tenter la suppression via le dépôt (qui gère les contraintes)
        return await self.address_repo.delete(address_id)

    async def set_user_default_address(self, address_id: int, user_id: int) -> None:
        """Définit l'adresse par défaut pour un utilisateur."""
        logger.debug(f"[AddrService] Définition défaut adresse ID: {address_id} pour user {user_id}")
        # Le dépôt gère la vérification d'appartenance
        success = await self.address_repo.set_default(user_id, address_id)
        if not success:
            # Le dépôt peut retourner False si l'adresse n'appartient pas à l'user
            raise HTTPException(status_code=404, detail="Adresse non trouvée ou n'appartient pas à l'utilisateur.") 