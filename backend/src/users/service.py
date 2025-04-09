"""
Module contenant la logique métier (services) pour les utilisateurs.

Utilise FastCRUD pour les opérations CRUD sur les utilisateurs.
"""
import logging
from typing import Optional

# Import FastCRUD et le modèle/schémas SQLModel
from fastcrud import FastCRUD
from src.users.models import User, UserCreate, UserRead, UserBase

# Import des fonctions de sécurité (hashage)
from src.auth.security import get_password_hash

# Import des exceptions et session DB
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class UserService:
    """Service pour gérer les opérations sur les utilisateurs avec FastCRUD."""

    def __init__(self, user_crud: FastCRUD, db: AsyncSession):
        self.user_crud = user_crud
        self.db = db

    async def create_user(self, user_data: UserCreate, is_admin: bool = False) -> UserRead:
        """Crée un nouvel utilisateur avec FastCRUD et retourne le schéma UserRead."""
        logger.debug(f"[UserService] Tentative de création utilisateur: {user_data.email}")

        # 1. Vérifier si l'email existe déjà
        user_exists = await self.user_crud.exists(db=self.db, email=user_data.email)
        if user_exists:
            logger.warning(f"[UserService] Email déjà existant: {user_data.email}")
            raise HTTPException(status_code=409, detail="Un compte avec cet email existe déjà.")

        # 2. Hacher le mot de passe
        hashed_password = get_password_hash(user_data.password)

        # 3. Préparer le dictionnaire de données pour FastCRUD (basé sur UserBase + password_hash)
        user_dict_to_create = {
            "email": user_data.email,
            "name": user_data.name,
            "password_hash": hashed_password,
            "is_admin": is_admin # is_admin vient de UserBase par défaut, mais on peut l'override ici
        }

        # 4. Appeler FastCRUD create
        try:
            # 'object' attend un dict ou un modèle Pydantic
            created_user_db: User = await self.user_crud.create(db=self.db, object=user_dict_to_create)
            logger.info(f"[UserService] Utilisateur créé avec ID: {created_user_db.id}")

            # 5. Retourner le schéma UserRead
            # On utilise model_validate pour convertir l'objet ORM en schéma Pydantic
            return UserRead.model_validate(created_user_db)

        except Exception as e:
            logger.error(f"[UserService] Erreur FastCRUD create pour {user_data.email}: {e}", exc_info=True)
            # Potentiellement rollback la session ici si non géré par middleware/dépendance
            # await self.db.rollback()
            raise HTTPException(status_code=500, detail="Erreur interne lors de la création de l'utilisateur.")

    async def get_user_by_id(self, user_id: int) -> UserRead:
        """Récupère un utilisateur par son ID via FastCRUD et retourne le schéma UserRead."""
        logger.debug(f"[UserService] Récupération utilisateur ID: {user_id}")

        # Utiliser FastCRUD get avec schema_to_select pour obtenir directement le bon schéma
        user_read_data: Optional[UserRead] = await self.user_crud.get(db=self.db, schema_to_select=UserRead, id=user_id)

        if not user_read_data:
             logger.warning(f"[UserService] Utilisateur ID {user_id} non trouvé via CRUD.")
             raise HTTPException(status_code=404, detail=f"Utilisateur avec ID {user_id} non trouvé.")

        logger.debug(f"[UserService] Utilisateur ID {user_id} trouvé et retourné en schéma UserRead.")
        return user_read_data

    # TODO: Ajouter méthode update_user(user_id: int, user_update: UserUpdate)
    # Utiliser self.user_crud.update(db=self.db, object=user_update_data, id=user_id)
    # Attention à ne pas permettre la modification du mot de passe directement ici.

    # TODO: Ajouter méthode delete_user(user_id: int)
    # Utiliser self.user_crud.delete(db=self.db, id=user_id) 