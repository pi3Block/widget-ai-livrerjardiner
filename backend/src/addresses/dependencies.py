import logging
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Importations nécessaires (chemins à vérifier/adapter)
from src.database import get_db_session # Chemin correcté pour être absolu depuis src
# Le modèle ORM n'est plus importé ici, le service utilise les fonctions CRUD
# from src.addresses.infrastructure.address_orm_model import AddressDB 
from src.addresses.service import AddressService # Chemin corrigé pour être absolu depuis src
# Import de FastCRUD n'est plus nécessaire ici si le service n'en dépend plus directement
# from fastcrud import FastCRUD

# Import des dépendances pour UserService
from src.users.service import UserService
from src.users.dependencies import get_user_service

# Interface Repository n'est plus nécessaire ici
# from src.addresses.domain.repositories import AbstractAddressRepository
# Implémentation Repository n'est plus nécessaire ici
# from src.addresses.infrastructure.address_sql_repository import AddressSQLRepository

logger = logging.getLogger(__name__)

# Commenté : Le CRUD n'est plus injecté directement dans le service
# def get_address_crud(...): ...
# AddressCrudDep = Annotated[FastCRUD, Depends(get_address_crud)]

# Dépendance pour obtenir le service d'adresses
def get_address_service(
    # address_crud: AddressCrudDep, # Supprimé
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service)] # Ajout UserService
) -> AddressService:
    """
    Fournit une instance du service d'adresses avec les dépendances nécessaires.
    
    Cette fonction est utilisée comme dépendance FastAPI pour injecter le service d'adresses
    dans les endpoints. Elle configure le service avec une session de base de données
    et le service utilisateur.
    
    Args:
        db: Session de base de données asynchrone
        user_service: Service de gestion des utilisateurs
        
    Returns:
        AddressService: Instance configurée du service d'adresses
    """
    logger.debug("Fourniture de AddressService avec DB Session et UserService")
    # Passer les dépendances nécessaires au constructeur du service
    return AddressService(db=db, user_service=user_service)

# Alias pour l'injection simplifiée du service
AddressServiceDep = Annotated[AddressService, Depends(get_address_service)]
