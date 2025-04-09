import logging
from typing import Optional, List, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body, Response

# Services Applicatifs (via dépendances du module courant)
from .dependencies import QuoteServiceDep 

# Schémas/DTOs (depuis models.py du module courant)
from .models import (
    QuoteRead, QuoteCreate, QuoteUpdate, PaginatedQuoteRead # Renommage vers Read
)

# Exceptions du module
from .exceptions import (
    QuoteNotFoundException, InvalidQuoteStatusException, QuoteUpdateForbiddenException
)
# Exceptions d'autres domaines (à vérifier si cet import est toujours correct)
from src.products.exceptions import VariantNotFoundException, InvalidOperationException # Correction potentiel chemin

# Dépendances d'Authentification (chemins à vérifier)
from src.auth.security import get_current_active_user, get_current_admin_user
from src.users.models import UserRead as UserResponseSchema # Utiliser le schéma Read de User

logger = logging.getLogger(__name__)

# --- Création du Routeur --- 
router = APIRouter( # Renommé en router pour cohérence
    prefix="/quotes",
    tags=["Quotes"]
)

# Dépendances d'authentification typées
CurrentUserDep = Annotated[UserResponseSchema, Depends(get_current_active_user)]
AdminUserDep = Annotated[UserResponseSchema, Depends(get_current_admin_user)] 

# --- Endpoints pour les Devis ---

@router.post("/", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
async def create_new_quote(
    quote_service: QuoteServiceDep,
    current_user: CurrentUserDep, 
    quote_request: QuoteCreate
):
    """Crée un nouveau devis pour l'utilisateur authentifié."""
    logger.info(f"API create_quote pour user ID: {current_user.id}")
    try:
        # Le service gère la validation et l'association à l'utilisateur
        # Assigner l'ID de l'utilisateur courant, écrasant celui du payload si différent
        if quote_request.user_id != current_user.id:
            logger.warning(f"Tentative de création de devis pour user ID {quote_request.user_id} par user {current_user.id}. Forçage à user {current_user.id}.")
            quote_request.user_id = current_user.id
            
        created_quote = await quote_service.create_quote(quote_request)
        return created_quote
    except VariantNotFoundException as e:
        logger.warning(f"Erreur création devis user {current_user.id}: variante non trouvée ({e})")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Variante produit non trouvée: {e.variant_id}")
    except InvalidOperationException as e:
        logger.warning(f"Erreur validation création devis user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API create_quote pour user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne création devis.")

@router.get("/{quote_id}", response_model=QuoteRead)
async def read_quote(
    quote_service: QuoteServiceDep,
    current_user: CurrentUserDep,
    quote_id: int = Path(..., title="ID du devis", ge=1)
):
    """Récupère un devis spécifique par son ID (accessible par le propriétaire ou admin)."""
    logger.info(f"API read_quote: ID={quote_id} par user {current_user.id}")
    try:
        # Passer is_admin basé sur le rôle de l'utilisateur courant
        is_admin = getattr(current_user, 'is_admin', False) # Assumer un champ is_admin dans UserResponseSchema
        quote = await quote_service.get_quote(quote_id, user_id=current_user.id, is_admin=is_admin)
        if not quote:
            raise QuoteNotFoundException(quote_id) # Lever l'exception domaine
        return quote
    except QuoteNotFoundException as e:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except QuoteUpdateForbiddenException as e:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur API read_quote {quote_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne récupération devis.")

@router.get("/", response_model=PaginatedQuoteRead) # Réponse paginée
async def list_my_quotes(
    quote_service: QuoteServiceDep,
    current_user: CurrentUserDep,
    response: Response, 
    limit: int = Query(20, ge=1, le=200, description="Nombre max de devis à retourner"),
    offset: int = Query(0, ge=0, description="Nombre de devis à sauter")
):
    """Liste les devis de l'utilisateur authentifié."""
    logger.info(f"API list_my_quotes pour user ID: {current_user.id}, limit={limit}, offset={offset}")
    try:
        quotes_list, total_count = await quote_service.list_user_quotes(user_id=current_user.id, limit=limit, offset=offset)
        # Construire la réponse paginée
        paginated_response = PaginatedQuoteRead(items=quotes_list, total=total_count)
        # Ajouter le header Content-Range
        end_range = offset + len(quotes_list) - 1 if quotes_list else offset
        response.headers["Content-Range"] = f"quotes {offset}-{end_range}/{total_count}"
        return paginated_response
    except Exception as e:
        logger.error(f"Erreur API list_my_quotes pour user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne listage devis.")

@router.patch("/{quote_id}/status", response_model=QuoteRead)
async def update_quote_status(
    quote_service: QuoteServiceDep,
    current_user: CurrentUserDep,
    quote_id: int = Path(..., title="ID du devis à MAJ", ge=1),
    status_update: QuoteUpdate = Body(...)
):
    """Met à jour le statut d'un devis (accessible par propriétaire ou admin)."""
    logger.info(f"API update_quote_status: ID={quote_id} à '{status_update.status}' par user {current_user.id}")
    try:
        is_admin = getattr(current_user, 'is_admin', False)
        updated_quote = await quote_service.update_quote_status(
            quote_id=quote_id, 
            status_update=status_update.status, 
            requesting_user_id=current_user.id, 
            is_admin=is_admin
        )
        return updated_quote
    except QuoteNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (InvalidQuoteStatusException, QuoteUpdateForbiddenException) as e:
        logger.warning(f"Erreur validation MAJ statut devis {quote_id}: {e}")
        # Utiliser 403 pour Forbidden, 400 pour invalide statut
        status_code = status.HTTP_403_FORBIDDEN if isinstance(e, QuoteUpdateForbiddenException) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e)) 
    except Exception as e:
        logger.error(f"Erreur API update_quote_status {quote_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne MAJ statut devis.") 