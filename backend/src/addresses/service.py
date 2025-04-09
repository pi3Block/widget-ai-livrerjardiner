"""
Module définissant le service pour la gestion des adresses.
"""
import logging
from typing import Optional

# Third-party imports
from fastapi import HTTPException

# First-party imports
from src.addresses.models import AddressCreate, AddressRead, AddressUpdate, AddressList
from src.addresses.interfaces.repositories import AbstractAddressRepository
from src.users.service import UserService
from src.users.models import User


logger = logging.getLogger(__name__)

class AddressService:
    """
    Service pour gérer la logique métier des adresses.
    
    Ce service encapsule la logique métier liée aux adresses,
    en utilisant le repository pour les opérations de base de données.
    """

    def __init__(self, repository: AbstractAddressRepository, user_service: UserService): 
        """
        Initialise le service avec un repository et un service utilisateur.
        
        Args:
            repository: Repository pour les opérations sur les adresses
            user_service: Service pour les opérations sur les utilisateurs
        """
        self.repository = repository
        self.user_service = user_service
        logger.info("AddressService initialisé avec UserService.")

    async def validate_address_ownership(self, address_id: int, user_id: int) -> bool:
        """
        Vérifie si une adresse existe et appartient à l'utilisateur.
        
        Args:
            address_id: Identifiant de l'adresse
            user_id: Identifiant de l'utilisateur
            
        Returns:
            bool: True si l'adresse appartient à l'utilisateur
            
        Raises:
            HTTPException: Si l'adresse n'existe pas ou n'appartient pas à l'utilisateur
        """
        logger.debug(f"[AddrService] Validation propriété adresse ID: {address_id} pour user {user_id}")
        address_db = await self.repository.get_by_id(address_id)
        if not address_db:
            logger.warning(f"[AddrService] Validation échouée: Adresse {address_id} non trouvée.")
            raise HTTPException(status_code=404, detail=f"Adresse ID {address_id} non trouvée.")
        
        if address_db.user_id != user_id:
            logger.warning(f"[AddrService] Validation échouée: Adresse {address_id} n'appartient pas à user {user_id}.")
            raise HTTPException(status_code=403, detail="Accès non autorisé à cette adresse.")
            
        logger.debug(f"[AddrService] Validation propriété adresse {address_id} réussie pour user {user_id}.")
        return True

    async def get_user_email(self, user_id: int) -> Optional[str]:
        """
        Récupère l'adresse email d'un utilisateur via UserService.
        
        Args:
            user_id: Identifiant de l'utilisateur
            
        Returns:
            Optional[str]: L'adresse email de l'utilisateur ou None
        """
        logger.debug(f"[AddrService] Récupération email pour user ID: {user_id}")
        try:
            user_schema: Optional[User] = await self.user_service.get_user_by_id(user_id)
            if user_schema:
                return user_schema.email
            else:
                logger.warning(f"[AddrService] Utilisateur ID {user_id} non trouvé via UserService lors de la recherche d'email.")
                return None
        except HTTPException as e:
            logger.error(f"[AddrService] Erreur UserService lors de get_user_by_id({user_id}): {e.detail}")
            return None
        except Exception as e:
            logger.exception(f"[AddrService] Erreur inattendue lors de la récupération de l'email pour user {user_id}: {e}")
            return None

    async def get_address_by_id(self, address_id: int, requesting_user_id: int) -> AddressRead:
        """
        Récupère une adresse par ID, vérifiant l'appartenance.
        
        Args:
            address_id: Identifiant de l'adresse
            requesting_user_id: Identifiant de l'utilisateur qui fait la demande
            
        Returns:
            AddressRead: L'adresse trouvée
            
        Raises:
            HTTPException: Si l'adresse n'existe pas ou n'appartient pas à l'utilisateur
        """
        logger.debug(f"[AddrService] Récupération adresse ID: {address_id} pour user {requesting_user_id}")
        address_db = await self.repository.get_by_id(address_id)
        if not address_db:
            raise HTTPException(status_code=404, detail="Adresse non trouvée.")
        
        if address_db.user_id != requesting_user_id:
            logger.warning(f"[AddrService] Tentative d'accès non autorisé à l'adresse {address_id} par user {requesting_user_id}")
            raise HTTPException(status_code=403, detail="Accès non autorisé à cette adresse.")
            
        return AddressRead.model_validate(address_db)

    async def list_user_addresses(self, user_id: int, skip: int = 0, limit: int = 1000) -> AddressList:
        """
        Liste les adresses d'un utilisateur.
        
        Args:
            user_id: Identifiant de l'utilisateur
            skip: Nombre d'adresses à sauter (pagination)
            limit: Nombre maximum d'adresses à récupérer
            
        Returns:
            AddressList: Liste des adresses et nombre total
        """
        logger.debug(f"[AddrService] Listage adresses pour user ID: {user_id}")
        return await self.repository.get_by_user_id(user_id, skip, limit)

    async def add_address_for_user(
        self,
        user_id: int,
        address_data: AddressCreate
    ) -> AddressRead:
        """
        Ajoute une nouvelle adresse pour un utilisateur.
        
        Args:
            user_id: Identifiant de l'utilisateur
            address_data: Données de l'adresse à créer
            
        Returns:
            AddressRead: L'adresse créée
            
        Raises:
            HTTPException: En cas d'erreur lors de la création
        """
        logger.debug(f"[AddrService] Ajout adresse pour user ID: {user_id}")
        
        existing_addresses = await self.list_user_addresses(user_id)
        is_first_address = existing_addresses.total == 0
        
        address_dict = address_data.model_dump()
        address_dict["user_id"] = user_id
        
        if is_first_address or (address_dict.get('is_default') and not any(addr.is_default for addr in existing_addresses.items)):
            address_dict["is_default"] = True
            if not is_first_address and any(addr.is_default for addr in existing_addresses.items):
                 logger.warning(f"[AddrService] Ajout d'une nouvelle adresse par défaut pour user {user_id} alors qu'une existait.")
        elif 'is_default' not in address_dict:
             address_dict["is_default"] = False

        try:
            # TODO: Implement or find address validation logic
            # validate_address_data(address_dict)
            created_address_db = await self.repository.create(address_dict)
            if created_address_db.is_default and not is_first_address:
                 await self.set_user_default_address(created_address_db.id, user_id)
                 created_address_db.is_default = True
            
            return AddressRead.model_validate(created_address_db)
        except ValueError as e:
            logger.error(f"[AddrService] Erreur validation adresse user {user_id}: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"[AddrService] Erreur CRUD ajout adresse user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne ajout adresse.")

    async def update_user_address(
        self,
        address_id: int,
        requesting_user_id: int,
        address_data: AddressUpdate
    ) -> AddressRead:
        """
        Met à jour une adresse pour un utilisateur.
        
        Args:
            address_id: Identifiant de l'adresse à mettre à jour
            requesting_user_id: Identifiant de l'utilisateur qui fait la demande
            address_data: Données de mise à jour
            
        Returns:
            AddressRead: L'adresse mise à jour
            
        Raises:
            HTTPException: Si l'adresse n'existe pas, n'appartient pas à l'utilisateur, ou en cas d'erreur
        """
        logger.debug(f"[AddrService] MAJ adresse ID: {address_id} pour user {requesting_user_id}")
        
        existing_address_schema = await self.get_address_by_id(address_id, requesting_user_id)
        
        update_payload = address_data.model_dump(exclude_unset=True)
        if update_payload.get('is_default') is True:
            if not existing_address_schema.is_default:
                 await self.set_user_default_address(address_id, requesting_user_id)
            update_payload.pop('is_default', None)
        elif update_payload.get('is_default') is False and existing_address_schema.is_default:
             other_addresses = await self.list_user_addresses(requesting_user_id)
             if other_addresses.total > 1:
                 raise HTTPException(status_code=400, detail="Impossible de retirer le statut par défaut. Définissez une autre adresse par défaut d'abord.")
             update_payload.pop('is_default', None)

        if update_payload: 
            try:
                # TODO: Implement or find address validation logic
                # validate_address_data(update_payload)
                updated_address_db = await self.repository.update(address_id, update_payload)
                if not updated_address_db:
                    raise HTTPException(status_code=404, detail="Adresse non trouvée lors MAJ.")
                
                final_address_db = await self.repository.get_by_id(address_id)
                return AddressRead.model_validate(final_address_db)

            except ValueError as e:
                logger.error(f"[AddrService] Erreur validation adresse {address_id}: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"[AddrService] Erreur CRUD MAJ adresse {address_id} user {requesting_user_id}: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Erreur interne MAJ adresse.")
        else:
            final_address_db = await self.repository.get_by_id(address_id)
            return AddressRead.model_validate(final_address_db)

    async def delete_user_address(self, address_id: int, requesting_user_id: int) -> None:
        """
        Supprime une adresse pour un utilisateur.
        
        Args:
            address_id: Identifiant de l'adresse à supprimer
            requesting_user_id: Identifiant de l'utilisateur qui fait la demande
            
        Raises:
            HTTPException: Si l'adresse n'existe pas, n'appartient pas à l'utilisateur, ou en cas d'erreur
        """
        logger.debug(f"[AddrService] Suppression adresse ID: {address_id} pour user {requesting_user_id}")
        
        # Vérifier que l'adresse existe et appartient à l'utilisateur
        address_db = await self.repository.get_by_id(address_id)
        if not address_db:
            raise HTTPException(status_code=404, detail="Adresse non trouvée.")
        
        if address_db.user_id != requesting_user_id:
            logger.warning(f"[AddrService] Tentative de suppression non autorisée de l'adresse {address_id} par user {requesting_user_id}")
            raise HTTPException(status_code=403, detail="Accès non autorisé à cette adresse.")
        
        # Vérifier si c'est l'adresse par défaut
        is_default = address_db.is_default
        
        try:
            # Supprimer l'adresse
            deleted_address = await self.repository.delete(address_id)
            if not deleted_address:
                raise HTTPException(status_code=404, detail="Adresse non trouvée lors de la suppression.")
            
            # Si c'était l'adresse par défaut, définir une autre adresse comme par défaut
            if is_default:
                other_addresses = await self.list_user_addresses(requesting_user_id)
                if other_addresses.total > 0:
                    # Définir la première adresse comme par défaut
                    await self.set_user_default_address(other_addresses.items[0].id, requesting_user_id)
                    logger.info(f"[AddrService] Nouvelle adresse par défaut définie pour user {requesting_user_id} après suppression.")
            
            logger.info(f"[AddrService] Adresse ID {address_id} supprimée pour user {requesting_user_id}.")
        except Exception as e:
            logger.error(f"[AddrService] Erreur lors de la suppression de l'adresse {address_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne lors de la suppression de l'adresse.")

    async def set_user_default_address(self, address_id: int, user_id: int) -> None:
        """
        Définit une adresse comme étant l'adresse par défaut pour un utilisateur.
        
        Args:
            address_id: Identifiant de l'adresse à définir par défaut
            user_id: Identifiant de l'utilisateur
            
        Raises:
            HTTPException: Si l'adresse n'existe pas ou n'appartient pas à l'utilisateur
        """
        logger.debug(f"[AddrService] Définition adresse ID {address_id} comme par défaut pour user {user_id}")
        
        # Vérifier que l'adresse existe et appartient à l'utilisateur
        address_db = await self.repository.get_by_id(address_id)
        if not address_db:
            raise HTTPException(status_code=404, detail="Adresse non trouvée.")
        
        if address_db.user_id != user_id:
            logger.warning(f"[AddrService] Tentative de définition non autorisée de l'adresse {address_id} comme par défaut par user {user_id}")
            raise HTTPException(status_code=403, detail="Accès non autorisé à cette adresse.")
        
        try:
            # Définir l'adresse comme par défaut
            await self.repository.set_default(address_id, user_id)
            logger.info(f"[AddrService] Adresse ID {address_id} définie comme par défaut pour user {user_id}.")
        except Exception as e:
            logger.error(f"[AddrService] Erreur lors de la définition de l'adresse {address_id} comme par défaut: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne lors de la définition de l'adresse par défaut.") 