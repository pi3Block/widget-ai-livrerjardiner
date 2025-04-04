from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

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

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> models.User:
    """Dépendance FastAPI pour obtenir l'utilisateur actuel à partir du token JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception
        
    # Utiliser run_in_threadpool si get_user_by_id fait des I/O bloquantes
    # user = await run_in_threadpool(crud.get_user_by_id, user_id=user_id)
    user = crud.get_user_by_id(user_id=user_id) # Supposons synchrone pour l'instant
    
    if user is None:
        raise credentials_exception
    return user

# Dépendance pour obtenir l'utilisateur actif (pourrait ajouter des vérifications de statut plus tard)
async def get_current_active_user(current_user: Annotated[models.User, Depends(get_current_user)]):
    # Ici, on pourrait vérifier si l'utilisateur est banni, désactivé, etc.
    # if current_user.disabled:
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user 