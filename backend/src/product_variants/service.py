import logging
from typing import Optional, List, Dict, Any, Tuple, TypeVar, Generic
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select
from fastcrud import FastCRUD

from .models import (
    ProductVariant, ProductVariantRead, ProductVariantCreate, ProductVariantUpdate,
    ProductVariantReadWithStockAndTags, ProductVariantTagLink
)
# Importation des services et modèles dépendants
from src.stock.services import StockService
from src.stock.models import StockRead, Stock # Importez le modèle Stock pour la création initiale
from src.tags.services import TagService
from src.tags.models import TagRead
from src.products.models import Product # Pour vérifier l'existence du produit

# Importer les exceptions spécifiques
from .exceptions import VariantNotFoundException, DuplicateSKUException # Ajouter les exceptions nécessaires
from src.products.exceptions import ProductNotFoundException
from src.stock.exceptions import StockNotFoundException, StockUpdateFailedException
from src.tags.exceptions import TagNotFoundException

logger = logging.getLogger(__name__)

# --- Pagination Schemas (Similaire à TagService) ---
T = TypeVar('T', bound=SQLModel)
class PaginatedResponse(SQLModel, Generic[T]):
    items: List[T]
    total: int
class PaginatedVariantResponse(PaginatedResponse[ProductVariantReadWithStockAndTags]): pass
# -----------------------------------------------------

class ProductVariantService:
    """Service applicatif pour la gestion des variations de produits."""

    def __init__(
        self,
        db: AsyncSession,
        variant_crud: FastCRUD[ProductVariant],
        product_crud: FastCRUD[Product], # Pour vérifier l'existence du produit parent
        stock_service: StockService,
        tag_service: TagService
    ):
        self.db = db
        self.variant_crud = variant_crud
        self.product_crud = product_crud
        self.stock_service = stock_service
        self.tag_service = tag_service
        logger.info("ProductVariantService initialized.")

    async def _get_variant_read_with_details(self, variant_entity: ProductVariant) -> ProductVariantReadWithStockAndTags:
        """Enrichit une entité ProductVariant avec les informations de stock et de tags."""
        # Valider l'entité de base
        variant_read = ProductVariantRead.model_validate(variant_entity)

        # Obtenir les informations de stock
        stock_info: Optional[StockRead] = None
        try:
            stock_info = await self.stock_service.get_stock_for_variant(variant_read.id)
        except StockNotFoundException:
            logger.warning(f"[VariantService] No stock record found for variant ID {variant_read.id}")
        except Exception as e:
            logger.error(f"[VariantService] Error fetching stock for variant {variant_read.id}: {e}", exc_info=True)

        # Obtenir les tags (ils sont déjà chargés via la relation si bien configurée)
        # Si les tags ne sont pas chargés automatiquement, utiliser tag_service pour les récupérer
        tags_read: List[TagRead] = [TagRead.model_validate(tag) for tag in variant_entity.tags]
        # Alternative si les tags ne sont pas chargés:
        # tag_ids = [link.tag_id for link in variant_entity.tag_links] # Assumer un modèle de lien accessible
        # tags_read = await self.tag_service.get_tags_by_ids(tag_ids) if tag_ids else []

        # Construire la réponse détaillée
        variant_details = ProductVariantReadWithStockAndTags(
            **variant_read.model_dump(),
            stock=stock_info,
            tags=tags_read
        )
        return variant_details

    async def get_variant(self, variant_id: int) -> Optional[ProductVariantReadWithStockAndTags]:
        """Récupère une variation détaillée par ID."""
        logger.debug(f"[VariantService] Get Variant ID: {variant_id}")
        # Charger la variation avec ses tags via la relation
        variant_entity = await self.variant_crud.get(id=variant_id, include_relations=["tags"])
        if not variant_entity:
            # raise VariantNotFoundException(variant_id)
            return None

        return await self._get_variant_read_with_details(variant_entity)

    async def list_variants_for_product(self, product_id: int, limit: int = 50, offset: int = 0) -> PaginatedVariantResponse:
        """Liste les variations pour un produit spécifique."""
        logger.debug(f"[VariantService] List Variants for Product ID: {product_id}, limit={limit}, offset={offset}")
        # Vérifier si le produit existe (optionnel mais recommandé)
        product_exists = await self.product_crud.exists(id=product_id)
        if not product_exists:
            raise ProductNotFoundException(product_id)

        variants_entities, total_count = await self.variant_crud.get_multi(
            limit=limit,
            offset=offset,
            filters={"product_id": product_id},
            include_relations=["tags"] # Charger les tags
        )

        variants_read: List[ProductVariantReadWithStockAndTags] = []
        for variant_entity in variants_entities:
            variant_detail = await self._get_variant_read_with_details(variant_entity)
            variants_read.append(variant_detail)

        return PaginatedVariantResponse(items=variants_read, total=total_count)

    async def create_variant(self, variant_data: ProductVariantCreate) -> ProductVariantReadWithStockAndTags:
        """Crée une nouvelle variation de produit."""
        logger.info(f"[VariantService] Create Variant for Product ID: {variant_data.product_id}, SKU: {variant_data.sku}")

        # 1. Vérifier l'existence du produit parent
        product_exists = await self.product_crud.exists(id=variant_data.product_id)
        if not product_exists:
            raise ProductNotFoundException(variant_data.product_id)

        # 2. Vérifier l'unicité du SKU (FastCRUD peut le gérer avec une contrainte unique)
        # Alternative: Vérification explicite
        # sku_exists = await self.variant_crud.exists(sku=variant_data.sku)
        # if sku_exists:
        #     raise DuplicateSKUException(variant_data.sku)

        # 3. Valider les Tag IDs fournis
        tags_to_link: List[Tag] = []
        if variant_data.tag_ids:
            tags_read = await self.tag_service.get_tags_by_ids(variant_data.tag_ids)
            if len(tags_read) != len(variant_data.tag_ids):
                # Trouver les IDs manquants
                found_ids = {tag.id for tag in tags_read}
                missing_ids = [tid for tid in variant_data.tag_ids if tid not in found_ids]
                raise TagNotFoundException(message=f"Tags non trouvés: {missing_ids}")
            # Convertir TagRead en Tag pour la relation (FastCRUD s'en charge normalement)
            # tags_to_link = [await self.tag_service.tag_crud.get(id=tr.id) for tr in tags_read]
            # Mieux: Laisser FastCRUD gérer la liaison via les IDs si possible

        # 4. Préparer les données pour la création de la variation
        # Extraire initial_stock et tag_ids car ils ne font pas partie de ProductVariantBase
        initial_stock = variant_data.initial_stock
        tag_ids = variant_data.tag_ids
        variant_payload = ProductVariantBase.model_validate(variant_data) # Base pour le CRUD

        try:
            # 5. Créer la variation (sans les tags initialement si FastCRUD ne lie pas par ID)
            created_variant_entity = await self.variant_crud.create(schema=variant_payload)

            # 6. Lier les tags (si FastCRUD ne l'a pas fait)
            # Si votre FastCRUD ou repo ne gère pas la liaison M2M par ID:
            # if tags_to_link:
            #     created_variant_entity.tags = tags_to_link # Assigner les objets Tag
            #     await self.db.commit()
            #     await self.db.refresh(created_variant_entity, attribute_names=["tags"])
            # Si FastCRUD gère la liaison via les IDs, c'est plus simple (à vérifier)
            if tag_ids:
                 # Supposer que le repo/CRUD a une méthode pour lier les tags
                 await self.variant_crud.update(id=created_variant_entity.id, schema=ProductVariantUpdate(tag_ids=tag_ids))
                 await self.db.refresh(created_variant_entity, attribute_names=['tags']) # Recharger la relation

            # 7. Créer l'enregistrement de stock initial
            if initial_stock is not None and initial_stock >= 0:
                await self.stock_service.create_or_update_stock(
                    variant_id=created_variant_entity.id,
                    quantity=initial_stock,
                    stock_alert_threshold=10 # Ou lire depuis config/constantes
                )
            else:
                 # Créer un enregistrement stock avec quantité 0 par défaut ?
                 await self.stock_service.create_or_update_stock(created_variant_entity.id, 0)

            logger.info(f"[VariantService] Variant ID {created_variant_entity.id} created with SKU {created_variant_entity.sku}.")

            # 8. Recharger et retourner la variation complète
            # Recharger avec les tags explicitement si la session a expiré ou pour être sûr
            final_variant = await self.variant_crud.get(id=created_variant_entity.id, include_relations=["tags"])
            if not final_variant:
                raise VariantNotFoundException(created_variant_entity.id, message="Impossible de recharger la variation après création.")

            return await self._get_variant_read_with_details(final_variant)

        except Exception as e: # Capturer les erreurs de contrainte (ex: SKU unique)
            logger.error(f"[VariantService] Error creating variant SKU {variant_data.sku}: {e}", exc_info=True)
            # Analyser l'erreur pour être plus spécifique
            # if "unique constraint" in str(e).lower() and "sku" in str(e).lower():
            #     raise DuplicateSKUException(variant_data.sku)
            # Gérer d'autres erreurs
            raise # Lever une exception de service

    async def update_variant(self, variant_id: int, variant_data: ProductVariantUpdate) -> Optional[ProductVariantReadWithStockAndTags]:
        """Met à jour une variation existante."""
        logger.info(f"[VariantService] Update Variant ID: {variant_id}")

        # 1. Vérifier si la variation existe
        variant_exists = await self.variant_crud.exists(id=variant_id)
        if not variant_exists:
            # raise VariantNotFoundException(variant_id)
            return None

        # 2. Valider les Tag IDs si fournis
        tags_to_set: Optional[List[int]] = variant_data.tag_ids # Garder les IDs pour FastCRUD
        if tags_to_set is not None: # Si la liste est fournie (même vide pour supprimer les tags)
            if tags_to_set: # Si la liste n'est pas vide, valider les IDs
                tags_read = await self.tag_service.get_tags_by_ids(tags_to_set)
                if len(tags_read) != len(tags_to_set):
                    found_ids = {tag.id for tag in tags_read}
                    missing_ids = [tid for tid in tags_to_set if tid not in found_ids]
                    raise TagNotFoundException(message=f"Tags non trouvés pour la mise à jour: {missing_ids}")
            # Si tags_to_set est une liste vide [], cela signifie supprimer tous les tags liés

        # 3. Préparer les données pour la mise à jour (exclure tag_ids si FastCRUD le gère séparément)
        # variant_payload = variant_data.model_copy(exclude={"tag_ids"} if tags_to_set is not None else None)
        variant_payload = variant_data # Laisser FastCRUD gérer la mise à jour M2M

        try:
            # 4. Mettre à jour la variation (y compris les liens de tags si FastCRUD le supporte)
            updated_variant_entity = await self.variant_crud.update(
                id=variant_id,
                schema=variant_payload,
                include_relations=["tags"] # Demander le rechargement des tags
            )

            if not updated_variant_entity:
                 # Devrait avoir levé NotFound si l'ID était mauvais
                 logger.warning(f"[VariantService] Update variant {variant_id} returned None unexpectedly.")
                 # Recharger pour être sûr
                 reloaded_variant = await self.variant_crud.get(id=variant_id, include_relations=["tags"])
                 if not reloaded_variant:
                      raise VariantNotFoundException(variant_id, "Impossible de trouver la variation après une tentative de mise à jour.")
                 updated_variant_entity = reloaded_variant

            logger.info(f"[VariantService] Variant ID {variant_id} updated.")

            # 5. Retourner la variation complète
            return await self._get_variant_read_with_details(updated_variant_entity)

        except Exception as e:
            logger.error(f"[VariantService] Error updating variant {variant_id}: {e}", exc_info=True)
            # Gérer les erreurs de contrainte (SKU unique sur une autre variation, etc.)
            # if "unique constraint" in str(e).lower() and "sku" in str(e).lower():
            #     raise DuplicateSKUException(variant_data.sku if variant_data.sku else "provided")
            raise

    async def delete_variant(self, variant_id: int) -> bool:
        """Supprime une variation. Gérer/Vérifier les dépendances (stock, commandes?)."""
        logger.info(f"[VariantService] Delete Variant ID: {variant_id}")

        # Vérifier les dépendances (ex: Commandes actives) avant suppression ? Ou laisser la DB gérer avec RESTRICT ?
        # Note: Le stock est supprimé par cascade DB (one-to-one/many)
        # Les liens de tags sont supprimés par cascade DB (many-to-many)

        try:
            deleted_variant = await self.variant_crud.delete(id=variant_id)
            if deleted_variant:
                logger.info(f"[VariantService] Variant ID {variant_id} deleted.")
                # Le stock associé est supprimé par cascade DB, pas besoin d'appel explicite à stock_service.delete
                return True
            else:
                # raise VariantNotFoundException(variant_id)
                return False # N'existait pas
        except Exception as e: # Capturer les erreurs de contrainte (ex: OrderItems avec ON DELETE RESTRICT)
            logger.error(f"[VariantService] Error deleting variant {variant_id}: {e}", exc_info=True)
            # Renvoyer une erreur indiquant une dépendance?
            # raise InvalidOperationException(f"Impossible de supprimer la variation {variant_id} à cause de dépendances.")
            raise 