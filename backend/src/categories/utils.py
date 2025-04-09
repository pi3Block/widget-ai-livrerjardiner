"""Fonctions utilitaires pour le module categories."""

from typing import Optional
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Category

async def check_category_exists(db: AsyncSession, name: str, exclude_id: Optional[int] = None) -> bool:
    """Vérifie si une catégorie avec le même nom existe déjà."""
    query = select(Category).where(Category.name == name)
    if exclude_id:
        query = query.where(Category.id != exclude_id)
    result = await db.exec(query)
    return result.first() is not None

async def check_parent_category(db: AsyncSession, parent_id: int) -> bool:
    """Vérifie si la catégorie parente existe et n'est pas la même que la catégorie courante."""
    result = await db.exec(select(Category).where(Category.id == parent_id))
    return result.first() is not None 