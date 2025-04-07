import logging
from typing import Optional, List, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body, Response

# Services Applicatifs (via dépendances)
from .dependencies import QuoteServiceDep

# Schémas/DTOs
from src.quotes.application.schemas import (
    QuoteResponse, QuoteCreate, QuoteUpdate, PaginatedQuoteResponse
)

# Exceptions du Domaine (pour mapping)
from src.quotes.domain.exceptions import (
    QuoteNotFoundException, InvalidQuoteStatusException, QuoteUpdateForbiddenException
)
from src.products.domain.exceptions import VariantNotFoundException # Possible à la création

# Dépendances d'Authentification
from src.core.security import get_current_active_user_entity, get_current_admin_user_entity
from src.users.domain.user_entity import UserEntity

logger = logging.getLogger(__name__)

# --- Création du Routeur --- 
quote_router = APIRouter(
    prefix="/quotes",
    tags=["Quotes"]
)

# Dépendances d'authentification typées
CurrentUserDep = Annotated[UserEntity, Depends(get_current_active_user_entity)]
AdminUserDep = Annotated[UserEntity, Depends(get_current_admin_user_entity)] # Si des endpoints admin sont ajoutés

# --- Endpoints pour les Devis ---

@quote_router.post("/", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_new_quote(
    quote_request: QuoteCreate,
    quote_service: QuoteServiceDep,
    current_user: CurrentUserDep
):
    """Crée un nouveau devis pour l'utilisateur authentifié."""
    logger.info(f"API create_quote pour user ID: {current_user.id}")
    try:
        # Le service gère la validation et l'association à l'utilisateur
        created_quote = await quote_service.create_quote(quote_request, current_user.id)
        return created_quote
    except VariantNotFoundException as e:
        logger.warning(f"Erreur création devis user {current_user.id}: variante non trouvée ({e})")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Variante produit non trouvée: {e}")
    except InvalidOperationException as e:
        logger.warning(f"Erreur validation création devis user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API create_quote pour user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne création devis.")

@quote_router.get("/{quote_id}", response_model=QuoteResponse)
async def read_quote(
    quote_service: QuoteServiceDep,
    current_user: CurrentUserDep,
    quote_id: int = Path(..., title="ID du devis", ge=1)
):
    """Récupère un devis spécifique par son ID (accessible par le propriétaire ou admin)."""
    logger.info(f"API read_quote: ID={quote_id} par user {current_user.id}")
    try:
        quote = await quote_service.get_quote(quote_id, user_id=current_user.id, is_admin=current_user.is_admin)
        if not quote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Devis non trouvé")
        return quote
    except QuoteUpdateForbiddenException as e:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API read_quote {quote_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne récupération devis.")

# Note: L'endpoint /users/me/quotes est maintenant géré par le user_router ou ici ?
# Pour garder la logique métier proche, on le met ici en filtrant sur l'utilisateur courant.
@quote_router.get("/", response_model=List[QuoteResponse]) # Changé de /users/me/quotes à /
async def list_my_quotes(
    response: Response, # Ajout du paramètre Response
    quote_service: QuoteServiceDep,
    current_user: CurrentUserDep,
    limit: int = Query(20, ge=1, le=200, description="Nombre max de devis à retourner"),
    offset: int = Query(0, ge=0, description="Nombre de devis à sauter")
):
    """Liste les devis de l'utilisateur authentifié."""
    logger.info(f"API list_my_quotes pour user ID: {current_user.id}, limit={limit}, offset={offset}")
    try:
        # Le service doit pouvoir retourner le total maintenant
        quotes, total_count = await quote_service.list_user_quotes(user_id=current_user.id, limit=limit, offset=offset)
        # Ajouter le header Content-Range
        end_range = offset + len(quotes) - 1 if quotes else offset
        response.headers["Content-Range"] = f"quotes {offset}-{end_range}/{total_count}"
        return quotes
    except Exception as e:
        logger.error(f"Erreur API list_my_quotes pour user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne listage devis.")

@quote_router.patch("/{quote_id}/status", response_model=QuoteResponse)
async def update_quote_status(
    quote_service: QuoteServiceDep,
    current_user: CurrentUserDep,
    quote_id: int = Path(..., title="ID du devis à MAJ", ge=1),
    status_update: QuoteUpdate = Body(...)
):
    """Met à jour le statut d'un devis (accessible par propriétaire ou admin)."""
    logger.info(f"API update_quote_status: ID={quote_id} à '{status_update.status}' par user {current_user.id}")
    try:
        updated_quote = await quote_service.update_quote_status(
            quote_id=quote_id, 
            status_update=status_update.status, 
            requesting_user_id=current_user.id, 
            is_admin=current_user.is_admin
        )
        return updated_quote
    except QuoteNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (InvalidQuoteStatusException, QuoteUpdateForbiddenException) as e:
        logger.warning(f"Erreur validation MAJ statut devis {quote_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) # Ou 403 pour Forbidden
    except Exception as e:
        logger.error(f"Erreur API update_quote_status {quote_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne MAJ statut devis.")

# Ajouter d'autres endpoints si nécessaire (ex: admin list all) 