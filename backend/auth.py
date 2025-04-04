from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

# Importer la session DB et le modèle UserDB
from database import get_db_session, AsyncSession
import crud
import models
import config

# Schéma pour les données contenues dans le token JWT
class TokenData(BaseModel):
    user_id: Optional[int] = None

# Schéma pour la réponse de l'endpoint de login
class Token(BaseModel):
    access_token: str
    token_type: str

# Configuration OAuth2 (indique l'URL de l'endpoint de login)
# "tokenUrl" sera l'endpoint que nous créerons dans main.py pour obtenir le token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crée un token JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Utiliser la durée configurée
        expire = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[int]:
    """Décode un token JWT et retourne l'ID utilisateur ou None si invalide/expiré."""
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        user_id: Optional[str] = payload.get("sub") # "sub" (subject) est conventionnellement utilisé pour l'ID
        if user_id is None:
            return None
        return int(user_id) # Retourne l'ID utilisateur
    except JWTError:
        # Token invalide (signature, expiration, etc.)
        return None

# Renommée pour clarifier, retourne UserDB ou lève une exception
async def get_current_user_db_from_token(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db_session) # Injecter la session DB
) -> models.UserDB:
    """Dépendance FastAPI pour obtenir l'objet UserDB à partir du token JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception
        
    # Utiliser la fonction crud asynchrone
    user_db = await crud.get_user_by_id(db=db, user_id=user_id)
    
    if user_db is None:
        # L'utilisateur existait lors de la création du token, mais plus maintenant?
        raise credentials_exception
    return user_db

# Dépendance principale pour obtenir l'utilisateur actif (retourne UserDB)
async def get_current_active_user(
    current_user_db: Annotated[models.UserDB, Depends(get_current_user_db_from_token)]
) -> models.UserDB:
    """Vérifie si l'utilisateur obtenu via le token est actif et le retourne."""
    # Ici, on pourrait vérifier si l'utilisateur est banni, désactivé, etc.
    # if current_user_db.disabled:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user_db

# Nouvelle dépendance pour obtenir un utilisateur admin actif
async def get_current_admin_user(
    current_user_db: Annotated[models.UserDB, Depends(get_current_active_user)]
) -> models.UserDB:
    """Vérifie que l'utilisateur actif est aussi administrateur."""
    if not current_user_db.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Administrator privileges required."
        )
    return current_user_db

# --- Optionnel: Dépendance pour obtenir l'utilisateur actif (ou None) --- 
async def get_optional_current_active_user(
    token: Annotated[str | None, Depends(oauth2_scheme)] = None, # Rendre le token optionnel
    db: AsyncSession = Depends(get_db_session)
) -> models.UserDB | None:
    """Récupère l'objet UserDB correspondant à l'utilisateur authentifié, ou None si non connecté/invalide."""
    if token is None:
        return None
    try:
        user_id = decode_access_token(token)
        if user_id is None:
            return None # Token valide mais sans ID?
        
        user_db = await crud.get_user_by_id(db, user_id=user_id)
        if user_db is None:
            return None # Utilisateur non trouvé en BDD
        
        # Vérification d'activité (si implémentée)
        # if user_db.disabled:
        #     return None 
            
        return user_db
    except Exception as e: # Attrape JWTError ou autre
        # Logguer l'erreur peut être utile ici
        print(f"Erreur lors de la récupération de l'utilisateur optionnel: {e}") # TODO: Remplacer par logger
        return None 