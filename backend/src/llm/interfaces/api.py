import logging
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# Schémas Pydantic pour la requête et la réponse
from pydantic import BaseModel

# Services et dépendances du domaine LLM
from src.llm.application.services import ChatService
from src.llm.infrastructure.ollama_client import OllamaClient
from src.llm.domain.llm_interface import AbstractLLM

# Dépendances globales (DB, User) - Correction des imports
from ...core.database import get_db_session # Correction chemin et nom
from ...core.security import get_optional_current_active_user_entity # Correction chemin et nom
from src.users.domain.user_entity import UserEntity # Pour typer current_user

# --- NOUVEAU: Importer les dépendances de repositories Produits ---
from src.products.interfaces.dependencies import VariantRepositoryDep, StockRepositoryDep
# --- NOUVEAU: Importer les dépendances de service Quotes ---
from src.quotes.interfaces.dependencies import QuoteServiceDep
# -----------------------------------------------------------------

# Domain
from src.products.domain.repositories import (
    AbstractProductVariantRepository, AbstractStockRepository
)
from src.quotes.application.services import QuoteService # Pour ChatService
from src.email.application.services import EmailService # Pour ChatService
from src.pdf.application.services import PDFService # Pour ChatService

# Application
from src.llm.application.services import ChatService

# Infrastructure
from src.llm.infrastructure.ollama_client import OllamaClient
# Dépendances des autres domaines
from src.products.interfaces.dependencies import VariantRepositoryDep, StockRepositoryDep
from src.quotes.interfaces.dependencies import QuoteServiceDep # Pour ChatService
from src.email.interfaces.dependencies import EmailServiceDep # Pour ChatService
from src.pdf.interfaces.dependencies import PDFServiceDep # <-- Importer la dépendance PDF

logger = logging.getLogger(__name__)

# --- Schémas Pydantic pour l'API ---

class ChatRequest(BaseModel):
    user_input: str
    model: str = "mistral" # Modèle par défaut

class ChatResponse(BaseModel):
    response: str

# --- Routeur FastAPI ---

llm_router = APIRouter(
    prefix="/llm",
    tags=["LLM Chat"]
)

# --- Fonctions de Dépendance ---

# Cache simple pour l'instance OllamaClient (évite réinitialisation à chaque requête)
# Note: Pour une application réelle, un singleton plus robuste serait mieux.
_llm_client_instance: Optional[OllamaClient] = None

def get_llm(
    # Potentiellement des paramètres de configuration ou Depends
) -> AbstractLLM:
    # Retourne une instance concrète, ex: OllamaClient
    return OllamaClient() # Ou lire la config pour choisir

LLMDep = Annotated[AbstractLLM, Depends(get_llm)]

def get_chat_service(
    llm: LLMDep,
    variant_repo: VariantRepositoryDep,
    stock_repo: StockRepositoryDep,
    quote_service: QuoteServiceDep, 
    email_service: EmailServiceDep, 
    pdf_service: PDFServiceDep # <-- Ajouter l'injection de PDFService
    # Ajouter ici d'autres dépendances nécessaires
) -> ChatService:
    """Injecte LLM, repositories produits, QuoteService, EmailService, PDFService et fournit ChatService."""
    return ChatService(
        llm=llm,
        variant_repo=variant_repo,
        stock_repo=stock_repo,
        quote_service=quote_service,
        email_service=email_service, 
        pdf_service=pdf_service # <-- Passer PDFService au constructeur
        # Passer les autres dépendances
    )

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]

# --- Endpoint API ---

@llm_router.post("/chat", response_model=ChatResponse)
async def handle_chat_endpoint(
    # Reordered non-default Annotated dependencies first
    chat_service: ChatServiceDep, 
    current_user: Optional[UserEntity] = Depends(get_optional_current_active_user_entity),
    # Default source parameter last
    request: ChatRequest = Body(...)
):
    """
    Endpoint principal pour interagir avec l'assistant IA.
    Prend l'input utilisateur et le modèle désiré en entrée.
    Retourne la réponse générée par le LLM après traitement par le ChatService.
    """
    try:
        logger.info(f"Requête API /chat reçue: model={request.model}, user={'logged in' if current_user else 'anonymous'}")
        # Le client LLM utilisé par le service est déterminé lors de l'injection
        # via get_llm_client -> OllamaClient._ensure_initialized -> OllamaClient._get_llm_instance
        # Cependant, le ChatService lui-même reçoit le nom du modèle demandé pour le logging/potentielle logique future.
        # Actuellement OllamaClient gère le choix du modèle (mistral ou meta), on passe juste l'info.
        response_text = await chat_service.handle_chat(
            user_input=request.user_input, 
            current_user=current_user,
            selected_model=request.model # On passe le nom du modèle demandé
        )
        return ChatResponse(response=response_text)
    except Exception as e:
        # Log l'erreur côté serveur
        logger.error(f"Erreur API /chat: {e}", exc_info=True)
        # Retourne une erreur HTTP générique au client
        raise HTTPException(status_code=500, detail="Erreur interne du serveur lors du traitement de la requête de chat.")

# On pourrait ajouter d'autres endpoints LLM ici si nécessaire (ex: gestion des modèles, etc.)
 