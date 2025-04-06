from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Import des fonctions de décodage depuis l'application user
from src.users.application import security as user_security

# Import du service User via sa dépendance
from src.users.application.services import UserService
from src.users.interfaces.dependencies import get_user_service # Assurez-vous que ce chemin est correct

# Import de l'entité domaine User
from src.users.domain.user_entity import UserEntity

# Schéma OAuth2
# Le tokenUrl pointe vers l'endpoint de login dans le nouveau routeur d'authentification
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") 

# Exception commune pour les erreurs d'authentification
CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

async def get_current_user_entity(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: Annotated[UserService, Depends(get_user_service)]
) -> UserEntity:
    """Dépendance pour obtenir l'entité User à partir du token Bearer."""
    user_id = user_security.decode_access_token(token)
    if user_id is None:
        raise CREDENTIALS_EXCEPTION
    
    try:
        # Utiliser le service pour récupérer l'utilisateur par ID
        user = await user_service.get_user_by_id(user_id)
    except HTTPException as e:
        # Si get_user_by_id lève 404, le transformer en 401
        if e.status_code == 404:
             raise CREDENTIALS_EXCEPTION
        else:
             raise e # Re-lever d'autres exceptions HTTP
    except Exception as e:
        # Gérer les erreurs inattendues du service
        # Log l'erreur est important ici
        print(f"Erreur récupération user via service: {e}") # Remplacer par logger
        raise HTTPException(status_code=500, detail="Internal server error during user retrieval.")

    if user is None: # Double vérification au cas où le service retournerait None sans exception
        raise CREDENTIALS_EXCEPTION
        
    return user

async def get_current_active_user_entity(
    current_user: Annotated[UserEntity, Depends(get_current_user_entity)]
) -> UserEntity:
    """Dépendance pour obtenir l'utilisateur actif (basé sur get_current_user_entity)."""
    # Ajouter ici la logique pour vérifier si l'utilisateur est actif si nécessaire
    # if not current_user.is_active: # Supposant un attribut is_active sur UserEntity
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user_entity(
    current_user: Annotated[UserEntity, Depends(get_current_active_user_entity)]
) -> UserEntity:
    """Dépendance pour obtenir un utilisateur admin actif."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Administrator privileges required."
        )
    return current_user

# --- Optionnel: Dépendance pour obtenir l'utilisateur actif (ou None) --- 
async def get_optional_current_active_user_entity(
    token: Annotated[str | None, Depends(oauth2_scheme)] = None, # Rendre le token optionnel
    user_service: Annotated[UserService, Depends(get_user_service)] = None # Rendre le service optionnel ici aussi
) -> Optional[UserEntity]:
    """Récupère l'entité User correspondante, ou None si non connecté/invalide."""
    if token is None or user_service is None: # Si pas de token ou problème injection service
        return None
    try:
        user_id = user_security.decode_access_token(token)
        if user_id is None:
            return None
        
        # Utiliser get_by_id du dépôt directement pourrait être une option pour éviter la HTTPException du service
        # user = await user_service.user_repo.get_by_id(user_id)
        # Ou capturer l'exception 404 du service
        try:
            user = await user_service.get_user_by_id(user_id)
        except HTTPException as e:
            if e.status_code == 404:
                return None
            else:
                # Logguer l'erreur inattendue
                print(f"Erreur récupération user optionnel via service: {e}") # Remplacer par logger
                return None
        
        if user is None:
             return None # Utilisateur non trouvé
        
        # Vérification d'activité si nécessaire
        # if not user.is_active:
        #     return None 
            
        return user
    except Exception as e: 
        print(f"Erreur récupération user optionnel: {e}") # Remplacer par logger
        return None 
