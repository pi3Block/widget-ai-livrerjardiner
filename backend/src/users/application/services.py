import logging
from typing import Optional

# Import de l'interface du dépôt et de l'entité
from src.users.domain.repositories import AbstractUserRepository
from src.users.domain.user_entity import UserEntity

# Import des fonctions de sécurité
from src.users.application import security

# Import des schémas (si besoin de DTOs spécifiques à l'application)
# from src.users.application import schemas as app_schemas

# Import des exceptions (si définies)
from fastapi import HTTPException # Utilisation temporaire

logger = logging.getLogger(__name__)

class AuthService:
    """Service pour gérer l'authentification des utilisateurs."""

    def __init__(self, user_repo: AbstractUserRepository):
        self.user_repo = user_repo

    async def authenticate_user(self, email: str, password: str) -> Optional[UserEntity]:
        """Authentifie un utilisateur. Retourne l'entité User si succès, sinon None."""
        logger.debug(f"[AuthService] Tentative d'authentification pour: {email}")
        
        # 1. Récupérer l'utilisateur par email via le dépôt
        try:
            user = await self.user_repo.get_by_email(email)
        except Exception as e:
            # Le dépôt devrait déjà logguer l'erreur DB
            logger.error(f"[AuthService] Erreur lors de la récupération de l'utilisateur {email}: {e}", exc_info=True)
            # Ne pas révéler de détails internes, retourner None ou lever une exception spécifique
            # raise AuthenticationError("Erreur interne lors de l'authentification")
            return None # Ou lever HTTPException(500) si on préfère

        if user is None:
            logger.warning(f"[AuthService] Utilisateur non trouvé: {email}")
            return None

        # 2. Vérifier le mot de passe en utilisant la fonction de sécurité
        if not security.verify_password(password, user.hashed_password):
            logger.warning(f"[AuthService] Mot de passe incorrect pour: {email}")
            return None

        # 3. Vérifier si l'utilisateur est actif (si cette logique existe)
        # if not user.is_active:
        #     logger.warning(f"[AuthService] Tentative de connexion d'un utilisateur inactif: {email}")
        #     return None

        logger.info(f"[AuthService] Authentification réussie pour: {email} (ID: {user.id})")
        return user # Retourne l'entité User du domaine

class UserService:
    """Service pour gérer les opérations sur les utilisateurs."""

    def __init__(self, user_repo: AbstractUserRepository):
        self.user_repo = user_repo

    async def create_user(self, email: str, password: str, name: Optional[str] = None, is_admin: bool = False) -> UserEntity:
        """Crée un nouvel utilisateur."""
        logger.debug(f"[UserService] Tentative de création utilisateur: {email}")

        # 1. Vérifier si l'email existe déjà
        existing_user = await self.user_repo.get_by_email(email)
        if existing_user:
            logger.warning(f"[UserService] Email déjà existant: {email}")
            raise HTTPException(status_code=409, detail="Un compte avec cet email existe déjà.")

        # 2. Préparer l'entité User (sans ID, created_at, updated_at)
        # Note: On passe le mot de passe en clair au constructeur de l'entité
        # MAIS le dépôt se chargera de le hacher AVANT de sauvegarder.
        # C'est un choix de conception: l'entité manipule des données conceptuelles,
        # le dépôt gère la persistance (incluant le hachage).
        # L'alternative serait de hacher ici et passer le hash à l'entité.
        from datetime import datetime # Import local pour les valeurs par défaut
        user_to_create = UserEntity(
            id=None, # L'ID sera assigné par la DB
            email=email,
            name=name,
            is_admin=is_admin,
            hashed_password=password, # Passe le mot de passe en clair au dépôt via l'entité
            created_at=datetime.now(), # Valeur temporaire, sera écrasée par DB
            updated_at=datetime.now()  # Valeur temporaire, sera écrasée par DB
        )

        # 3. Appeler le dépôt pour ajouter l'utilisateur
        try:
            created_user = await self.user_repo.add(user_to_create)
            logger.info(f"[UserService] Utilisateur créé avec ID: {created_user.id}")
            return created_user
        except HTTPException as http_exc: # Re-lever les exceptions HTTP (comme 409)
            raise http_exc
        except Exception as e:
            logger.error(f"[UserService] Erreur lors de l'ajout via le dépôt pour {email}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur interne lors de la création de l'utilisateur.")

    async def get_user_by_id(self, user_id: int) -> Optional[UserEntity]:
        """Récupère un utilisateur par son ID."""
        logger.debug(f"[UserService] Récupération utilisateur ID: {user_id}")
        user = await self.user_repo.get_by_id(user_id)
        if not user:
             raise HTTPException(status_code=404, detail=f"Utilisateur avec ID {user_id} non trouvé.")
        return user
    
    # Ajouter d'autres méthodes de service si nécessaire (update, delete, etc.)
