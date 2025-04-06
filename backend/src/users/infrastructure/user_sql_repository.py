import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, NoResultFound
import bcrypt

# Import de l'interface et de l'entité du domaine
from src.users.domain.repositories import AbstractUserRepository
from src.users.domain.user_entity import UserEntity

# Import du modèle ORM
from src.users.infrastructure.user_orm_model import UserDB

# Import des exceptions spécifiques ou génériques
from fastapi import HTTPException # Ou définir des exceptions de domaine/infra

logger = logging.getLogger(__name__)

def _map_orm_to_entity(user_db: UserDB) -> UserEntity:
    """Convertit un objet UserDB (ORM) en UserEntity (Domaine)."""
    if not user_db:
        return None
    return UserEntity(
        id=user_db.id,
        email=user_db.email,
        name=user_db.name,
        is_admin=user_db.is_admin,
        hashed_password=user_db.password_hash, # On garde le hash
        created_at=user_db.created_at,
        updated_at=user_db.updated_at
    )

class UserSQLRepository(AbstractUserRepository):
    """Implémentation SQLAlchemy du dépôt des utilisateurs."""

    def __init__(self, session: AsyncSession):
        self.db = session

    async def get_by_id(self, user_id: int) -> Optional[UserEntity]:
        logger.debug(f"[Repo] Récupération User ID: {user_id}")
        try:
            user_db = await self.db.get(UserDB, user_id)
            if not user_db:
                logger.warning(f"[Repo] User ID {user_id} non trouvé.")
                return None
            return _map_orm_to_entity(user_db)
        except Exception as e:
            logger.error(f"[Repo] Erreur DB get_by_id User ID {user_id}: {e}", exc_info=True)
            # Lever une exception spécifique serait mieux
            raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération de l'utilisateur.")

    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        logger.debug(f"[Repo] Récupération User par email: {email}")
        try:
            stmt = select(UserDB).where(UserDB.email == email)
            result = await self.db.execute(stmt)
            user_db = result.scalar_one_or_none()
            if not user_db:
                logger.debug(f"[Repo] Email {email} non trouvé.")
                return None
            return _map_orm_to_entity(user_db)
        except Exception as e:
            logger.error(f"[Repo] Erreur DB get_by_email {email}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne lors de la recherche par email.")

    async def get_by_id_with_addresses(self, user_id: int) -> Optional[UserEntity]:
        # --- Implémentation future --- 
        # Nécessitera de charger les AddressDB liées, de les mapper en AddressEntity,
        # et potentiellement d'adapter UserEntity pour les contenir.
        # Pour l'instant, on retourne le résultat simple.
        logger.warning("[Repo] get_by_id_with_addresses non complètement implémenté, retourne sans adresses.")
        return await self.get_by_id(user_id)
        # Exemple d'implémentation future (nécessite AddressEntity et mapper):
        # try:
        #     stmt = select(UserDB).options(selectinload(UserDB.addresses)).where(UserDB.id == user_id)
        #     result = await self.db.execute(stmt)
        #     user_db = result.scalar_one_or_none()
        #     if not user_db:
        #         return None
        #     user_entity = _map_orm_to_entity(user_db)
        #     # Assumer qu'on a un _map_address_orm_to_entity et que UserEntity a un champ addresses
        #     user_entity.addresses = [_map_address_orm_to_entity(addr_db) for addr_db in user_db.addresses]
        #     return user_entity
        # except Exception as e:
        #     logger.error(f"[Repo] Erreur DB get_by_id_with_addresses {user_id}: {e}", exc_info=True)
        #     raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération de l'utilisateur avec adresses.")

    async def add(self, user_entity: UserEntity) -> UserEntity:
        logger.debug(f"[Repo] Ajout utilisateur: {user_entity.email}")
        
        # 1. Hacher le mot de passe (la logique est ici, pas dans l'entité)
        try:
            password_bytes = user_entity.hashed_password.encode('utf-8') # Attention: suppose que le mot de passe non haché est passé dans hashed_password pour la création
            hashed_password_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
            hashed_password = hashed_password_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"[Repo] Erreur hachage mot de passe pour {user_entity.email}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne lors de la sécurisation du mot de passe.")

        # 2. Créer l'instance ORM
        user_db = UserDB(
            email=user_entity.email,
            name=user_entity.name,
            password_hash=hashed_password, # Utilise le hash généré
            is_admin=user_entity.is_admin # Assurez-vous que is_admin est dans UserEntity
            # created_at et updated_at sont gérés par la DB (server_default)
        )

        # 3. Ajouter à la session et gérer les erreurs
        try:
            self.db.add(user_db)
            await self.db.flush() # Pour obtenir l'ID et gérer les erreurs d'intégrité tôt
            await self.db.refresh(user_db) # Pour charger les valeurs par défaut (created_at)
            logger.info(f"[Repo] Utilisateur ajouté ID: {user_db.id} pour email: {user_db.email}")
            return _map_orm_to_entity(user_db) # Retourne l'entité mise à jour
        except IntegrityError as e: # Gère spécifiquement les erreurs d'intégrité (ex: email unique)
            await self.db.rollback() # Important de rollback
            logger.warning(f"[Repo] Erreur d'intégrité lors de l'ajout (email déjà existant?): {user_entity.email} - {e}")
            raise HTTPException(status_code=409, detail="Un compte avec cet email existe déjà.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"[Repo] Erreur DB lors de l'ajout de l'utilisateur {user_entity.email}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne lors de la création de l'utilisateur.")

    async def update(self, user_entity: UserEntity) -> Optional[UserEntity]:
        logger.debug(f"[Repo] Mise à jour User ID: {user_entity.id}")
        try:
            user_db = await self.db.get(UserDB, user_entity.id)
            if not user_db:
                logger.warning(f"[Repo] User ID {user_entity.id} non trouvé pour mise à jour.")
                return None

            # Mettre à jour les champs modifiables
            # Ne pas mettre à jour email ou password ici (gérer séparément si nécessaire)
            user_db.name = user_entity.name
            user_db.is_admin = user_entity.is_admin
            # updated_at est géré par la DB (onupdate)

            self.db.add(user_db) # Ajouter à la session pour marquer comme modifié
            await self.db.flush()
            await self.db.refresh(user_db)
            logger.info(f"[Repo] Utilisateur ID {user_db.id} mis à jour.")
            return _map_orm_to_entity(user_db)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"[Repo] Erreur DB lors de la mise à jour User ID {user_entity.id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne lors de la mise à jour de l'utilisateur.")

    async def delete(self, user_id: int) -> bool:
        logger.debug(f"[Repo] Suppression User ID: {user_id}")
        try:
            user_db = await self.db.get(UserDB, user_id)
            if not user_db:
                logger.warning(f"[Repo] User ID {user_id} non trouvé pour suppression.")
                return False
            
            await self.db.delete(user_db)
            await self.db.flush()
            logger.info(f"[Repo] Utilisateur ID {user_id} supprimé.")
            return True
        except Exception as e:
            await self.db.rollback()
            # Gérer spécifiquement les erreurs de clé étrangère si nécessaire
            logger.error(f"[Repo] Erreur DB lors de la suppression User ID {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne lors de la suppression de l'utilisateur.")

# --- Remarques --- 
# - La gestion des transactions (commit/rollback) est supposée être gérée par la dépendance FastAPI qui fournit la session.
# - Le hachage du mot de passe est fait ici lors de l'ajout.
# - La vérification du mot de passe (authenticate) n'est pas dans le dépôt, elle sera dans un service applicatif.
# - La méthode get_by_id_with_addresses n'est pas complètement implémentée.
