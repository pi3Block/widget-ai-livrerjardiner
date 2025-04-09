from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastcrud import FastCRUD

from src.database import get_db_session
from src.tags.models import Tag
from src.tags.service import TagService

# CRUD pour Tag
def get_tag_crud(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> FastCRUD[Tag]:
    """
    Fournit une instance de FastCRUD pour les tags.
    
    Args:
        session: Session de base de données asynchrone
        
    Returns:
        FastCRUD[Tag]: Instance de FastCRUD configurée pour le modèle Tag
    """
    return FastCRUD(Tag, session)

TagCRUDDep = Annotated[FastCRUD[Tag], Depends(get_tag_crud)]

# Service Tag
def get_tag_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tag_crud: Annotated[FastCRUD[Tag], Depends(get_tag_crud)]
) -> TagService:
    """
    Fournit une instance du service de gestion des tags.
    
    Args:
        session: Session de base de données asynchrone
        tag_crud: Instance de FastCRUD pour les tags
        
    Returns:
        TagService: Instance du service de gestion des tags
    """
    return TagService(db=session, tag_crud=tag_crud)

TagServiceDep = Annotated[TagService, Depends(get_tag_service)] 