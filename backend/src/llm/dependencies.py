"""
Dépendances pour le module LLM.
"""
from typing import Generator, Annotated, Optional

from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from src.database import get_db_session
from llm.llm_service import LLMService
from llm.service import ChatService
from llm.exceptions import LLMRequestNotFoundError
from llm.llm_interface import AbstractLLM
from llm.ollama_client import OllamaClient

# --- Dépendances d'autres modules (nécessaires pour ChatService) ---
from src.products.interfaces.dependencies import VariantRepositoryDep, StockRepositoryDep
from src.quotes.interfaces.dependencies import QuoteServiceDep
from email.dependencies import EmailServiceDep
from src.pdf.interfaces.dependencies import PDFServiceDep

# --- Dépendances pour LLMService ---

def get_llm_service(db: Session = Depends(get_db_session)) -> LLMService:
    """Fournit une instance du service LLM de base."""
    return LLMService(db)

LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]

def get_request_by_id(
    request_id: int,
    service: LLMServiceDep # Utiliser l'alias annoté
) -> Generator:
    """
    Récupère une requête LLM par son ID via le service.
    
    Args:
        request_id: ID de la requête
        service: Service LLM injecté
        
    Yields:
        LLMRequest: La requête trouvée
        
    Raises:
        HTTPException: Si la requête n'est pas trouvée
    """
    try:
        # Le service LLMService est maintenant synchrone, pas besoin d'await
        request = service.get_request(request_id)
        yield request
    except LLMRequestNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requête LLM {request_id} non trouvée"
        )

# --- Dépendances pour ChatService ---

# Cache simple pour l'instance OllamaClient
_llm_client_instance: Optional[OllamaClient] = None

def get_llm(
    # Potentiellement des paramètres de configuration ou Depends
) -> AbstractLLM:
    """Fournit une instance du client LLM (actuellement Ollama)."""
    # Pourrait être amélioré avec un singleton ou basé sur la config
    global _llm_client_instance
    if _llm_client_instance is None:
        _llm_client_instance = OllamaClient()
    return _llm_client_instance

LLMDep = Annotated[AbstractLLM, Depends(get_llm)]

def get_chat_service(
    llm: LLMDep,
    variant_repo: VariantRepositoryDep,
    stock_repo: StockRepositoryDep,
    quote_service: QuoteServiceDep, 
    email_service: EmailServiceDep, 
    pdf_service: PDFServiceDep,
    # Ajouter OrderServiceDep si nécessaire
    db_session: Annotated[AsyncSession, Depends(get_db_session)] # Ajout session async si besoin
) -> ChatService:
    """Injecte les dépendances et fournit ChatService."""
    # Note: Le ChatService actuel semble nécessiter d'autres dépendances
    # comme OrderService, AddressRepository qui ne sont pas injectées ici.
    # Il faudra les ajouter si on utilise ce service tel quel.
    return ChatService(
        llm=llm,
        variant_repo=variant_repo,
        stock_repo=stock_repo,
        quote_service=quote_service,
        email_service=email_service, 
        pdf_service=pdf_service
        # Passer les autres dépendances ici (order_service, address_repo...)
    )

ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)] 