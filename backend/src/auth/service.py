"""
Service d'authentification pour l'API.

Contient la logique métier pour:
- L'authentification des utilisateurs
- La vérification des tokens JWT
- L'obtention des informations utilisateur à partir d'un token
"""
import logging
from typing import Optional

from fastcrud import FastCRUD
from sqlalchemy.ext.asyncio import AsyncSession

# Importations locales
from src.auth.security import verify_password, decode_access_token
from src.users.models import User, UserRead

logger = logging.getLogger(__name__)

class AuthService:
    """Service pour gérer l'authentification des utilisateurs avec FastCRUD."""

    def __init__(self, user_crud: FastCRUD, db: AsyncSession):
        self.user_crud = user_crud
        self.db = db

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authentifie un utilisateur par email et mot de passe.
        Retourne le modèle User (table) si succès, sinon None.
        """
        logger.debug(f"[AuthService] Tentative d'authentification pour: {email}")

        # 1. Récupérer l'utilisateur par email via FastCRUD
        # Spécifier schema_to_select=None pour obtenir l'objet ORM complet
        user: Optional[User] = await self.user_crud.get(db=self.db, schema_to_select=None, email=email)

        if user is None:
            logger.warning(f"[AuthService] Utilisateur non trouvé: {email}")
            return None

        # 2. Vérifier le mot de passe haché (utiliser user.password_hash)
        if not verify_password(password, user.password_hash):
            logger.warning(f"[AuthService] Mot de passe incorrect pour: {email}")
            return None

        # 3. Vérifier si l'utilisateur est actif (si cette logique existe)
        # Ajouter une colonne `is_active` au modèle User si nécessaire
        # if not user.is_active:
        #     logger.warning(f"[AuthService] Tentative de connexion d'un utilisateur inactif: {email}")
        #     return None

        logger.info(f"[AuthService] Authentification réussie pour: {email} (ID: {user.id})")
        return user  # Retourne le modèle User complet

    async def get_user_from_token(self, token: str) -> Optional[UserRead]:
        """
        Récupère un utilisateur à partir d'un token JWT.
        Retourne le schéma UserRead si succès, sinon None.
        """
        logger.debug("[AuthService] Récupération utilisateur depuis token")

        # 1. Décoder le token pour obtenir l'ID utilisateur
        user_id = decode_access_token(token)
        if user_id is None:
            logger.warning("[AuthService] Token invalide ou expiré")
            return None

        # 2. Récupérer l'utilisateur par ID via FastCRUD avec schema_to_select=UserRead
        try:
            user: Optional[UserRead] = await self.user_crud.get(
                db=self.db,
                schema_to_select=UserRead,
                id=user_id
            )
            if user is None:
                logger.warning(f"[AuthService] Utilisateur ID {user_id} du token non trouvé en base")
                return None

            # 3. Vérifier si l'utilisateur est actif (si cette logique existe)
            # if not user.is_active:
            #     logger.warning(f"[AuthService] Utilisateur inactif: ID {user_id}")
            #     return None

            logger.debug(f"[AuthService] Utilisateur récupéré depuis token: ID {user_id}")
            return user

        except Exception as e:
            logger.error(f"[AuthService] Erreur lors de la récupération de l'utilisateur ID {user_id}: {e}", exc_info=True)
            return None 