import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func as sql_func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, NoResultFound

# Import de l'interface et de l'entité du domaine
from src.addresses.domain.repositories import AbstractAddressRepository
from src.addresses.domain.address_entity import AddressEntity

# Import du modèle ORM
from src.addresses.infrastructure.address_orm_model import AddressDB
# Import du modèle OrderDB pour la vérification de suppression
# (Chemin à vérifier/adapter lors de la refacto Order)
from src.database.models import OrderDB 

# Import des exceptions spécifiques ou génériques
from fastapi import HTTPException

logger = logging.getLogger(__name__)

def _map_orm_to_entity(address_db: AddressDB) -> AddressEntity:
    """Convertit un objet AddressDB (ORM) en AddressEntity (Domaine)."""
    if not address_db:
        return None
    return AddressEntity(
        id=address_db.id,
        user_id=address_db.user_id,
        street=address_db.street,
        city=address_db.city,
        zip_code=address_db.zip_code,
        country=address_db.country,
        is_default=address_db.is_default,
        created_at=address_db.created_at,
        updated_at=address_db.updated_at
    )

class AddressSQLRepository(AbstractAddressRepository):
    """Implémentation SQLAlchemy du dépôt des adresses."""

    def __init__(self, session: AsyncSession):
        self.db = session

    async def get_by_id(self, address_id: int) -> Optional[AddressEntity]:
        logger.debug(f"[Repo Adr] Récupération Adresse ID: {address_id}")
        try:
            address_db = await self.db.get(AddressDB, address_id)
            return _map_orm_to_entity(address_db)
        except Exception as e:
            logger.error(f"[Repo Adr] Erreur DB get_by_id Adresse ID {address_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne récupération adresse.")

    async def list_by_user_id(self, user_id: int) -> List[AddressEntity]:
        logger.debug(f"[Repo Adr] Listage adresses pour User ID: {user_id}")
        try:
            stmt = select(AddressDB).where(AddressDB.user_id == user_id).order_by(AddressDB.id)
            result = await self.db.execute(stmt)
            addresses_db = result.scalars().all()
            return [_map_orm_to_entity(addr) for addr in addresses_db]
        except Exception as e:
            logger.error(f"[Repo Adr] Erreur DB list_by_user_id {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne listage adresses.")

    async def get_default_by_user_id(self, user_id: int) -> Optional[AddressEntity]:
        logger.debug(f"[Repo Adr] Recherche adresse défaut pour User ID: {user_id}")
        try:
            stmt = select(AddressDB).where(AddressDB.user_id == user_id, AddressDB.is_default == True)
            result = await self.db.execute(stmt)
            address_db = result.scalar_one_or_none()
            return _map_orm_to_entity(address_db)
        except Exception as e:
            logger.error(f"[Repo Adr] Erreur DB get_default_by_user_id {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne recherche adresse défaut.")

    async def add(self, address_entity: AddressEntity) -> AddressEntity:
        logger.debug(f"[Repo Adr] Ajout adresse pour User ID: {address_entity.user_id}")
        
        # Vérifier combien d'adresses l'utilisateur a déjà
        existing_addresses_stmt = select(sql_func.count(AddressDB.id)).where(AddressDB.user_id == address_entity.user_id)
        address_count_result = await self.db.execute(existing_addresses_stmt)
        address_count = address_count_result.scalar_one()
        set_as_default = address_count == 0
        
        address_db = AddressDB(
            user_id=address_entity.user_id,
            street=address_entity.street,
            city=address_entity.city,
            zip_code=address_entity.zip_code,
            country=address_entity.country,
            is_default=set_as_default # Défaut si c'est la première
            # created_at/updated_at gérés par DB
        )
        try:
            self.db.add(address_db)
            await self.db.flush()
            await self.db.refresh(address_db)
            logger.info(f"[Repo Adr] Adresse ID {address_db.id} ajoutée pour user {address_entity.user_id}. Défaut={set_as_default}")
            # Si on a mis celle-ci par défaut, s'assurer que les autres ne le sont plus
            if set_as_default and address_count > 0: # Devrait être 0 ici mais sécurité
                 await self._unset_other_defaults(address_entity.user_id, address_db.id)

            return _map_orm_to_entity(address_db)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"[Repo Adr] Erreur DB ajout adresse user {address_entity.user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne ajout adresse.")

    async def update(self, address_entity: AddressEntity) -> Optional[AddressEntity]:
        logger.debug(f"[Repo Adr] MAJ adresse ID: {address_entity.id}")
        try:
            address_db = await self.db.get(AddressDB, address_entity.id)
            if not address_db:
                logger.warning(f"[Repo Adr] Adresse ID {address_entity.id} non trouvée pour MAJ.")
                return None

            # Mettre à jour les champs (is_default n'est pas MAJ ici)
            address_db.street = address_entity.street
            address_db.city = address_entity.city
            address_db.zip_code = address_entity.zip_code
            address_db.country = address_entity.country
            # updated_at géré par DB

            self.db.add(address_db)
            await self.db.flush()
            await self.db.refresh(address_db)
            logger.info(f"[Repo Adr] Adresse ID {address_db.id} mise à jour.")
            return _map_orm_to_entity(address_db)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"[Repo Adr] Erreur DB MAJ adresse {address_entity.id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne MAJ adresse.")

    async def delete(self, address_id: int) -> bool:
        logger.debug(f"[Repo Adr] Suppression adresse ID: {address_id}")
        try:
            address_db = await self.db.get(AddressDB, address_id)
            if not address_db:
                logger.warning(f"[Repo Adr] Adresse ID {address_id} non trouvée pour suppression.")
                return False
            
            # Vérifications (adresse par défaut, utilisée dans commandes)
            if address_db.is_default:
                logger.warning(f"[Repo Adr] Tentative suppression adresse par défaut ID {address_id}.")
                raise HTTPException(status_code=400, detail="Impossible de supprimer l'adresse par défaut.")
            
            order_check_stmt = select(sql_func.count(OrderDB.id)).where(
                or_(
                    OrderDB.delivery_address_id == address_id,
                    OrderDB.billing_address_id == address_id
                )
            )
            order_count_result = await self.db.execute(order_check_stmt)
            order_count = order_count_result.scalar_one()
            if order_count > 0:
                logger.warning(f"[Repo Adr] Tentative suppression adresse {address_id} utilisée dans {order_count} commandes.")
                raise HTTPException(status_code=400, detail=f"Impossible de supprimer l'adresse car utilisée dans {order_count} commande(s).")

            await self.db.delete(address_db)
            await self.db.flush()
            logger.info(f"[Repo Adr] Adresse ID {address_id} supprimée.")
            return True
        except HTTPException as e:
            # Re-lever les exceptions HTTP levées par les vérifications
            raise e
        except Exception as e:
            await self.db.rollback()
            logger.error(f"[Repo Adr] Erreur DB suppression adresse {address_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne suppression adresse.")

    async def set_default(self, user_id: int, address_id: int) -> bool:
        logger.debug(f"[Repo Adr] Définition adresse défaut ID {address_id} pour User ID {user_id}")
        try:
            # Vérifier que l'adresse appartient bien à l'utilisateur
            address_to_set = await self.db.get(AddressDB, address_id)
            if not address_to_set or address_to_set.user_id != user_id:
                 logger.warning(f"[Repo Adr] Adresse {address_id} non trouvée ou n'appartient pas à user {user_id} pour set_default.")
                 return False # Ou lever 404?
            
            # Mettre toutes les autres adresses de cet user à False
            await self._unset_other_defaults(user_id, address_id)
            
            # Mettre l'adresse cible à True
            address_to_set.is_default = True
            self.db.add(address_to_set)
            await self.db.flush()
            logger.info(f"[Repo Adr] Adresse ID {address_id} définie comme défaut pour user {user_id}.")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"[Repo Adr] Erreur DB set_default adresse {address_id} user {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne définition adresse défaut.")

    async def _unset_other_defaults(self, user_id: int, exclude_address_id: int):
        """Helper pour mettre is_default=False sur les autres adresses de l'utilisateur."""
        stmt_update_others = (
            update(AddressDB)
            .where(AddressDB.user_id == user_id, AddressDB.id != exclude_address_id)
            .values(is_default=False)
        )
        await self.db.execute(stmt_update_others)
        logger.debug(f"[Repo Adr Helper] unset_other_defaults exécuté pour user {user_id} (excluant {exclude_address_id})") 