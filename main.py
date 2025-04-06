from datetime import timedelta
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from typing import Annotated

from . import models, auth
from .config import config

router = APIRouter()

@router.post("/login")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user_db = await auth.authenticate_user(form_data.username, form_data.password)
    if not user_db:
        return {"error": "Incorrect username or password"}

    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": str(user_db['id'])},
        expires_delta=access_token_expires
    )
    return models.Token(access_token=access_token, token_type="bearer") 