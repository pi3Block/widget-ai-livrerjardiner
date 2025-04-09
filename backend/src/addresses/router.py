import logging
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status

# --- Imports Corrigés et Ajoutés ---
from src.auth.dependencies import get_current_active_user
from src.users.models import UserRead as UserSchema
from src.addresses.models import AddressCreate, AddressRead, AddressUpdate
from src.addresses.dependencies import AddressServiceDep

# Exceptions
from src.addresses.exceptions import AddressNotFoundException, CannotDeleteDefaultAddressException

logger = logging.getLogger(__name__)

# Création du routeur FastAPI
router = APIRouter(
    prefix="/addresses",
    tags=["Addresses"]
)

# Dépendance pour obtenir l'utilisateur courant
CurrentUserDep = Annotated[UserSchema, Depends(get_current_active_user)]

@router.post("", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
async def create_address(
    address_data: AddressCreate,
    current_user: CurrentUserDep,
    address_service: AddressServiceDep
):
    """
    Crée une nouvelle adresse pour l'utilisateur actuellement authentifié.
    """
    logger.info(f"[AddrRouter] Tentative ajout adresse pour user {current_user.id}")
    try:
        new_address = await address_service.add_address_for_user(
            user_id=current_user.id,
            address_data=address_data
        )
        return new_address
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[AddrRouter] Erreur ajout adresse user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne ajout adresse.")

@router.get("", response_model=List[AddressRead])
async def list_addresses(
    current_user: CurrentUserDep,
    address_service: AddressServiceDep
):
    """
    Récupère la liste des adresses de l'utilisateur actuellement authentifié.
    """
    logger.info(f"[AddrRouter] Listage adresses pour user {current_user.id}")
    try:
        addresses = await address_service.list_user_addresses(user_id=current_user.id)
        return addresses
    except Exception as e:
        logger.error(f"[AddrRouter] Erreur listage adresses user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne listage adresses.")

@router.get("/{address_id}", response_model=AddressRead)
async def read_address(
    address_id: int,
    current_user: CurrentUserDep,
    address_service: AddressServiceDep
):
    """
    Récupère les détails d'une adresse spécifique par son ID.
    L'utilisateur doit être le propriétaire de l'adresse.
    """
    logger.info(f"[AddrRouter] Lecture adresse ID {address_id} pour user {current_user.id}")
    try:
        address = await address_service.get_address_by_id(
            address_id=address_id,
            requesting_user_id=current_user.id
        )
        return address
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[AddrRouter] Erreur lecture adresse {address_id} user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne lecture adresse.")

@router.put("/{address_id}", response_model=AddressRead)
async def update_address(
    address_id: int,
    address_data: AddressUpdate,
    current_user: CurrentUserDep,
    address_service: AddressServiceDep
):
    """
    Met à jour une adresse existante appartenant à l'utilisateur courant.
    Seuls les champs fournis dans le corps de la requête seront mis à jour.
    """
    logger.info(f"[AddrRouter] Tentative MAJ adresse ID {address_id} pour user {current_user.id}")
    try:
        updated_address = await address_service.update_user_address(
            address_id=address_id,
            requesting_user_id=current_user.id,
            address_data=address_data
        )
        return updated_address
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[AddrRouter] Erreur MAJ adresse {address_id} user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne MAJ adresse.")

@router.patch("/{address_id}/set-default", status_code=status.HTTP_204_NO_CONTENT)
async def set_default_address(
    address_id: int,
    current_user: CurrentUserDep,
    address_service: AddressServiceDep
):
    """
    Définit une adresse spécifique comme étant l'adresse par défaut 
    pour l'utilisateur courant.
    """
    logger.info(f"[AddrRouter] Tentative définition défaut adresse ID {address_id} pour user {current_user.id}")
    try:
        await address_service.set_user_default_address(
            address_id=address_id,
            user_id=current_user.id
        )
        return
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[AddrRouter] Erreur set_default adresse {address_id} user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne définition adresse par défaut.")

@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: int,
    current_user: CurrentUserDep,
    address_service: AddressServiceDep
):
    """
    Supprime une adresse appartenant à l'utilisateur courant.
    Ne peut pas supprimer l'adresse par défaut s'il en existe d'autres.
    """
    logger.info(f"[AddrRouter] Tentative suppression adresse ID {address_id} pour user {current_user.id}")
    try:
        await address_service.delete_user_address(
            address_id=address_id,
            requesting_user_id=current_user.id
        )
        return
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[AddrRouter] Erreur suppression adresse {address_id} user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne suppression adresse.") 