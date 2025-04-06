import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

# Import du service applicatif via dépendances
from src.addresses.application.services import AddressService
from src.addresses.interfaces.dependencies import get_address_service
from src.addresses.domain.address_entity import AddressEntity

# Import des schémas API
from src.addresses.interfaces import address_api_schemas as schemas

# Import de l'entité domaine User (pour typer l'utilisateur courant)
from src.users.domain.user_entity import UserEntity
# Import de la dépendance de sécurité pour obtenir l'utilisateur courant
from src.core.security import get_current_active_user_entity

logger = logging.getLogger(__name__)

# Créer le routeur pour les adresses
# Préfixe ajusté pour refléter le chemin original
address_router = APIRouter(prefix="/users/me/addresses", tags=["User Addresses"])


# Mapper une entité AddressEntity vers un schéma API Address
def map_entity_to_schema(entity: AddressEntity) -> schemas.Address:
    return schemas.Address.model_validate(entity)


@address_router.post("", response_model=schemas.Address, status_code=status.HTTP_201_CREATED)
async def add_user_address(
    address_in: schemas.AddressCreate,
    current_user: Annotated[UserEntity, Depends(get_current_active_user_entity)],
    address_service: Annotated[AddressService, Depends(get_address_service)]
):
    logger.info(f"[AddrRouter] Ajout d'adresse pour l'utilisateur ID: {current_user.id}")
    try:
        created_address_entity = await address_service.add_address_for_user(
            user_id=current_user.id,
            street=address_in.street,
            city=address_in.city,
            zip_code=address_in.zip_code,
            country=address_in.country
        )
        return map_entity_to_schema(created_address_entity)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[AddrRouter] Erreur inattendue ajout adresse user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne ajout adresse.")

@address_router.get("", response_model=List[schemas.Address])
async def get_my_addresses(
    current_user: Annotated[UserEntity, Depends(get_current_active_user_entity)],
    address_service: Annotated[AddressService, Depends(get_address_service)]
):
    logger.info(f"[AddrRouter] Listage adresses pour user ID: {current_user.id}")
    try:
        address_entities = await address_service.list_user_addresses(user_id=current_user.id)
        return [map_entity_to_schema(addr) for addr in address_entities]
    except Exception as e:
        logger.error(f"[AddrRouter] Erreur listage adresses user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne récupération adresses.")

@address_router.put("/{address_id}/default", status_code=status.HTTP_204_NO_CONTENT)
async def set_my_default_address(
    address_id: int,
    current_user: Annotated[UserEntity, Depends(get_current_active_user_entity)],
    address_service: Annotated[AddressService, Depends(get_address_service)]
):
    logger.info(f"[AddrRouter] Définition défaut adresse ID: {address_id} pour user {current_user.id}")
    try:
        await address_service.set_user_default_address(user_id=current_user.id, address_id=address_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[AddrRouter] Erreur définition défaut adresse {address_id} user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne définition adresse défaut.")

@address_router.put("/{address_id}", response_model=schemas.Address)
async def update_my_address(
    address_id: int,
    address_in: schemas.AddressUpdate,
    current_user: Annotated[UserEntity, Depends(get_current_active_user_entity)],
    address_service: Annotated[AddressService, Depends(get_address_service)]
):
    logger.info(f"[AddrRouter] Tentative MAJ adresse ID {address_id} pour user {current_user.id}")
    try:
        updated_address_entity = await address_service.update_user_address(
            address_id=address_id,
            requesting_user_id=current_user.id,
            street=address_in.street,
            city=address_in.city,
            zip_code=address_in.zip_code,
            country=address_in.country
        )
        return map_entity_to_schema(updated_address_entity)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[AddrRouter] Erreur MAJ adresse {address_id} user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne MAJ adresse.")

@address_router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_address(
    address_id: int,
    current_user: Annotated[UserEntity, Depends(get_current_active_user_entity)],
    address_service: Annotated[AddressService, Depends(get_address_service)]
):
    logger.info(f"[AddrRouter] Tentative suppression adresse ID {address_id} pour user {current_user.id}")
    try:
        deleted = await address_service.delete_user_address(address_id=address_id, requesting_user_id=current_user.id)
        # Le service lève 404 si non trouvée/non autorisée, ou 400 si contrainte.
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[AddrRouter] Erreur suppression adresse {address_id} user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne suppression adresse.") 