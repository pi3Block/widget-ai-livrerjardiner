"""
Routes principales pour le module LLM.

Ce fichier contient les endpoints API pour les interactions de chat
et la gestion des requêtes LLM.
"""
import logging
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
# Utiliser AsyncSession car ChatService est async
from src.llm.models import LLMRequest
from src.llm.service import LLMService
# Importer les exceptions depuis le domaine consolidé
from src.llm.exceptions import (
    LLMRequestNotFoundError,
    LLMAPIError,
    LLMRateLimitError,
    LLMInvalidPromptError,
    LLMInvalidModelError,
    LLMTimeoutError
)
# Importer les dépendances et alias depuis dependencies.py
from .dependencies import ChatServiceDep, LLMServiceDep, get_request_by_id

# Auth & User Schemas (imports relatifs pour la robustesse)
from ...core.security import get_optional_current_active_user 
from ...users.interfaces.user_api_schemas import User as UserResponseSchema

logger = logging.getLogger(__name__)

router = APIRouter(
    # Déplacer le préfixe ici si on veut que toutes les routes commencent par /llm
    # prefix="/llm", 
    tags=["LLM"] # Un tag unique pour toutes les routes LLM
)

# --- Schémas Pydantic pour l'API de Chat ---

class ChatRequest(BaseModel):
    user_input: str
    model: str = "mistral" # Modèle par défaut

class ChatResponse(BaseModel):
    response: str

# --- Endpoint API de Chat (depuis api.py) ---

@router.post("/chat", response_model=ChatResponse)
async def handle_chat_endpoint(
    # Utiliser les dépendances annotées depuis dependencies.py
    chat_service: ChatServiceDep, 
    current_user: Annotated[Optional[UserResponseSchema], Depends(get_optional_current_active_user)] = None,
    request: ChatRequest = Body(...)
):
    """
    Endpoint principal pour interagir avec l'assistant IA.
    Prend l'input utilisateur et le modèle désiré en entrée.
    Retourne la réponse générée par le LLM après traitement par le ChatService.
    """
    try:
        logger.info(f"Requête API /chat reçue: model={request.model}, user={'logged in' if current_user else 'anonymous'}")
        response_text = await chat_service.handle_chat(
            user_input=request.user_input, 
            current_user=current_user,
            selected_model=request.model
        )
        return ChatResponse(response=response_text)
    except Exception as e:
        logger.error(f"Erreur API /chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne du serveur lors du traitement de la requête de chat.")


# --- Endpoints pour la gestion des requêtes LLM (depuis l'ancien router.py) ---

# Endpoint pour créer une requête LLM (optionnel, peut être redondant avec /chat)
# Si on le garde, il faudrait peut-être utiliser LLMServiceDep
# @router.post("/requests", response_model=LLMRequest, tags=["LLM Admin"])
# async def create_llm_request(
#     request_data: LLMRequestBase,
#     service: LLMServiceDep
# ):
#     try:
#         request = service.create_request(request_data)
#         return request
#     except (LLMInvalidPromptError, LLMInvalidModelError) as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.get("/requests/{request_id}", response_model=LLMRequest, tags=["LLM Admin"])
async def get_llm_request(
    request: LLMRequest = Depends(get_request_by_id) # Utilise la dépendance qui gère le 404
):
    """
    Récupère une requête LLM par son ID.
    
    Args:
        request: Requête LLM injectée par la dépendance get_request_by_id
        
    Returns:
        LLMRequest: La requête trouvée
    """
    return request

@router.get("/requests", response_model=List[LLMRequest], tags=["LLM Admin"])
async def get_llm_user_requests(
    service: LLMServiceDep,
    user_id: Optional[int] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Récupère les requêtes LLM (potentiellement filtrées par utilisateur).
    
    Args:
        user_id: ID de l'utilisateur (optionnel)
        limit: Nombre maximum de requêtes à récupérer
        offset: Décalage pour la pagination
        service: Service LLM injecté
        
    Returns:
        List[LLMRequest]: Liste des requêtes
    """
    try:
        # Le service LLMService est synchrone, pas besoin d'await
        if user_id:
            # Note: La session DB est gérée dans le service via son constructeur
            return service.get_user_requests(user_id, limit, offset)
        else:
            # TODO: Implémenter la récupération de toutes les requêtes dans LLMService
            # Pour l'instant, retourne une liste vide si aucun user_id n'est fourni.
            # return service.get_all_requests(limit, offset)
            logger.warning("Récupération de toutes les requêtes LLM non implémentée.")
            return []
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des requêtes LLM: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne du serveur.") 