import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel
from fastcrud import FastCRUD

from .models import Tag, TagCreate, TagRead, TagUpdate
# Importer d'autres modèles si nécessaire pour les relations

# Importer les exceptions spécifiques aux tags
# from .exceptions import TagNotFoundException, DuplicateTagNameException

# --- Pagination Schemas (Copier ou définir ici si nécessaire) ---
# from src.shared.schemas import PaginatedResponse # Exemple
# class PaginatedTagResponse(PaginatedResponse[TagRead]): pass
# Ou définir simplement ici:
T = SQLModel
class PaginatedResponse(SQLModel, Generic[T]):
    items: List[T]
    total: int
class PaginatedTagResponse(PaginatedResponse[TagRead]): pass
# -------------------------------------------------------------

logger = logging.getLogger(__name__)

class TagService:
    """Service applicatif pour la gestion des tags."""

    def __init__(self, db: AsyncSession, tag_crud: FastCRUD[Tag]):
        self.db = db
        self.tag_crud = tag_crud
        logger.info("TagService initialized.")

    async def list_tags(self, limit: int = 100, offset: int = 0) -> PaginatedTagResponse:
        """Liste les tags avec pagination."""
        logger.debug(f"[Service] List Tags: limit={limit}, offset={offset}")
        try:
            tags, total_count = await self.tag_crud.get_multi(
                limit=limit,
                offset=offset,
                schema_to_select=TagRead,
                sort_by="name" # Trier par nom par exemple
            )
            return PaginatedTagResponse(items=tags, total=total_count)
        except Exception as e:
            logger.error(f"[Service] Error listing tags: {e}", exc_info=True)
            # Gérer l'erreur (ex: lever une exception de service)
            raise

    async def create_tag(self, tag_data: TagCreate) -> TagRead:
        """Crée un nouveau tag."""
        logger.info(f"[Service] Create Tag: {tag_data.name}")
        # Vérifier si le tag existe déjà (FastCRUD peut gérer cela avec des contraintes uniques)
        # try:
        #     existing = await self.tag_crud.get(filters={"name": tag_data.name})
        #     if existing:
        #         raise DuplicateTagNameException(tag_data.name)
        # except NoResultFound:
        #     pass # Le tag n'existe pas, c'est bon

        try:
            created_tag = await self.tag_crud.create(schema=tag_data, schema_to_select=TagRead)
            logger.info(f"[Service] Tag ID {created_tag.id} created.")
            return created_tag
        except Exception as e: # Capturer des erreurs potentielles de contrainte DB
            logger.error(f"[Service] Error creating tag {tag_data.name}: {e}", exc_info=True)
            # Vérifier si c'est une erreur de duplicata
            # if "unique constraint" in str(e).lower():
            #     raise DuplicateTagNameException(tag_data.name)
            raise # Lever une exception générique ou spécifique

    async def get_tag(self, tag_id: int) -> Optional[TagRead]:
        """Récupère un tag par ID."""
        logger.debug(f"[Service] Get Tag ID: {tag_id}")
        tag = await self.tag_crud.get(id=tag_id, schema_to_select=TagRead)
        # if not tag:
        #     raise TagNotFoundException(tag_id)
        return tag

    async def update_tag(self, tag_id: int, tag_data: TagUpdate) -> Optional[TagRead]:
        """Met à jour un tag existant."""
        logger.info(f"[Service] Update Tag ID: {tag_id}")
        # Vérifier l'unicité du nom si fourni
        # if tag_data.name:
        #     try:
        #         existing = await self.tag_crud.get(filters={"name": tag_data.name})
        #         if existing and existing.id != tag_id:
        #             raise DuplicateTagNameException(tag_data.name)
        #     except NoResultFound:
        #         pass

        try:
            updated_tag = await self.tag_crud.update(id=tag_id, schema=tag_data, schema_to_select=TagRead)
            if not updated_tag:
                # raise TagNotFoundException(tag_id)
                return None # Ou lever une exception
            logger.info(f"[Service] Tag ID {tag_id} updated.")
            return updated_tag
        except Exception as e:
            logger.error(f"[Service] Error updating tag {tag_id}: {e}", exc_info=True)
            # Gérer les erreurs potentielles (contraintes, etc.)
            raise

    async def delete_tag(self, tag_id: int) -> bool:
        """Supprime un tag."""
        logger.info(f"[Service] Delete Tag ID: {tag_id}")
        try:
            # FastCRUD delete retourne l'objet supprimé ou None
            deleted_tag = await self.tag_crud.delete(id=tag_id)
            if deleted_tag:
                logger.info(f"[Service] Tag ID {tag_id} deleted.")
                return True
            else:
                # raise TagNotFoundException(tag_id)
                return False # Le tag n'existait pas
        except Exception as e:
            logger.error(f"[Service] Error deleting tag {tag_id}: {e}", exc_info=True)
            # Gérer les erreurs (ex: contraintes de clé étrangère si non gérées par cascade)
            raise

    async def get_tags_by_ids(self, tag_ids: List[int]) -> List[TagRead]:
        """Récupère plusieurs tags par leurs IDs."""
        if not tag_ids:
            return []
        logger.debug(f"[Service] Get Tags by IDs: {tag_ids}")
        tags, _ = await self.tag_crud.get_multi(
            filters={"id__in": tag_ids},
            schema_to_select=TagRead
        )
        return tags 