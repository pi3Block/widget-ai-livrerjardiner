"""
Service pour la gestion des requêtes LLM.
"""
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlmodel import Session, select
# Utiliser AsyncSession car AbstractLLM.invoke est async
from sqlalchemy.ext.asyncio import AsyncSession 
# Importer desc explicitement
from sqlalchemy import desc 

from src.llm.models import LLMRequest, LLMRequestBase, LLMResponse
from src.llm.domain.exceptions import (
    LLMRequestNotFoundError,
    LLMAPIError,
    LLMRateLimitError,
    LLMInvalidPromptError,
    LLMInvalidModelError,
    LLMTimeoutError
)
from src.llm.constants import (
    REQUEST_STATUS_PENDING,
    REQUEST_STATUS_PROCESSING,
    REQUEST_STATUS_COMPLETED,
    REQUEST_STATUS_FAILED,
    REQUEST_STATUS_TIMEOUT,
    MODEL_GPT_3_5_TURBO,
    MODEL_GPT_4,
    MODEL_GPT_4_TURBO,
    # Les messages d'erreur ne sont plus nécessaires ici si on utilise les exceptions
)
# Import des utilitaires centralisés
from src.llm.utils import (
    validate_prompt,
    format_llm_request_reference,
    calculate_tokens, # Garder l'utilitaire actuel pour l'instant
    format_chat_messages, # Utiliser pour formater les messages
    measure_execution_time
)
from src.llm.config import settings
# Importer l'interface LLM et une implémentation (ex: Ollama)
from llm.llm_interface import AbstractLLM
# On pourrait injecter une instance via le constructeur ou la config
# Pour simplifier, on utilise OllamaClient directement pour l'instant
from llm.ollama_client import OllamaClient 

class LLMService:
    """Service pour la gestion des requêtes LLM."""
    
    # Injecter AbstractLLM et utiliser AsyncSession
    def __init__(self, db_session: AsyncSession, llm_client: AbstractLLM):
        """
        Initialise le service LLM.
        
        Args:
            db_session: Session de base de données asynchrone
            llm_client: Client LLM conforme à l'interface AbstractLLM
        """
        self.db_session = db_session
        self.llm_client = llm_client
    
    # Méthode asynchrone car la session et l'appel LLM sont async
    async def create_request(self, request_data: LLMRequestBase, user_id: Optional[int] = None) -> LLMRequest:
        """
        Crée une nouvelle requête LLM.
        
        Args:
            request_data: Données de la requête
            user_id: ID de l'utilisateur (optionnel)
            
        Returns:
            LLMRequest: Requête créée
            
        Raises:
            LLMInvalidPromptError: Si le prompt est invalide
            LLMInvalidModelError: Si le modèle est invalide
        """
        # Valider le prompt via l'utilitaire
        if not validate_prompt(request_data.prompt):
            raise LLMInvalidPromptError("Le prompt est trop long ou vide")
        
        # Valider le modèle (peut être déplacé vers la config/constantes)
        # Si llm_client gère les modèles, on peut déléguer cette validation
        # if request_data.model not in self.llm_client.get_supported_models():
        if request_data.model not in [MODEL_GPT_3_5_TURBO, MODEL_GPT_4, MODEL_GPT_4_TURBO]: # Garder la validation simple pour l'instant
            raise LLMInvalidModelError(request_data.model)
        
        # Créer la requête
        request = LLMRequest(
            **request_data.model_dump(), # Utiliser model_dump() pour Pydantic v2+
            user_id=user_id,
            status=REQUEST_STATUS_PENDING
        )
        
        # Sauvegarder en base de données (async)
        self.db_session.add(request)
        await self.db_session.commit()
        await self.db_session.refresh(request)
        
        return request
    
    # Méthode asynchrone car la session est async
    async def get_request(self, request_id: int) -> LLMRequest:
        """
        Récupère une requête LLM par son ID.
        
        Args:
            request_id: ID de la requête
            
        Returns:
            LLMRequest: Requête trouvée
            
        Raises:
            LLMRequestNotFoundError: Si la requête n'est pas trouvée
        """
        # Utiliser la session async pour get
        request = await self.db_session.get(LLMRequest, request_id)
        
        if not request:
            raise LLMRequestNotFoundError(request_id)
        
        return request
    
    # Méthode asynchrone car la session et l'appel LLM sont async
    @measure_execution_time
    async def process_request(self, request_id: int) -> Dict[str, Any]:
        """
        Traite une requête LLM en utilisant le client LLM injecté.
        
        Args:
            request_id: ID de la requête
            
        Returns:
            Dict[str, Any]: Résultat du traitement (incluant le temps d'exécution)
            
        Raises:
            LLMRequestNotFoundError: Si la requête n'est pas trouvée
            LLMAPIError: Si l'API LLM échoue
            LLMRateLimitError: Si la limite de taux est dépassée (géré par le client LLM?)
            LLMTimeoutError: Si la requête expire (géré par le client LLM?)
        """
        # Récupérer la requête (async)
        request = await self.get_request(request_id)
        
        # Mettre à jour le statut (async)
        request.status = REQUEST_STATUS_PROCESSING
        # Commit non nécessaire ici, sera fait après l'appel LLM
        
        try:
            # --- Appel réel au LLM via l'interface ---
            # Formater le message si nécessaire (ici, prompt simple)
            # Si c'était un chat, on utiliserait format_chat_messages
            formatted_prompt = request.prompt 
            
            # Utiliser le client LLM injecté
            response_text = await self.llm_client.invoke(
                prompt=formatted_prompt, 
                model=request.model, 
                # Passer d'autres paramètres si supportés par l'interface/implémentation
                # temperature=request.temperature, 
                # max_tokens=request.max_tokens
            )
            # --- Fin Appel réel au LLM ---
            
            # Mettre à jour la requête avec la réponse (async)
            request.status = REQUEST_STATUS_COMPLETED
            request.response = response_text
            # Utiliser l'utilitaire pour calculer les tokens
            request.tokens_used = calculate_tokens(request.prompt) + calculate_tokens(response_text)
            # Le temps de traitement sera ajouté par le décorateur
            
            await self.db_session.commit()
            await self.db_session.refresh(request) # Rafraîchir pour avoir les dernières données
            
            # Retourner les infos pertinentes
            return {
                "request_id": request.id,
                "status": request.status,
                "response": request.response,
                "tokens_used": request.tokens_used,
                # "processing_time": sera ajouté par le décorateur
            }
            
        except Exception as e:
            # Gérer les erreurs (async)
            request.status = REQUEST_STATUS_FAILED
            request.error = str(e)
            await self.db_session.commit()
            
            # Log l'erreur
            # logger.error(f"Erreur traitement requête {request_id}: {e}", exc_info=True)

            # Relancer des exceptions spécifiques basées sur l'erreur du client LLM
            # Le client LLM devrait idéalement lever des exceptions standardisées
            if isinstance(e, LLMRateLimitError): # Exemple
                 raise e
            elif isinstance(e, LLMTimeoutError): # Exemple
                 raise e
            else: # Erreur générique de l'API LLM
                 raise LLMAPIError(f"Erreur lors de l'appel LLM: {str(e)}") from e
    
    # Méthode asynchrone car la session est async
    async def get_user_requests(self, user_id: int, limit: int = 10, offset: int = 0) -> List[LLMRequest]:
        """
        Récupère les requêtes LLM d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            limit: Nombre maximum de requêtes à récupérer
            offset: Offset pour la pagination
            
        Returns:
            List[LLMRequest]: Liste des requêtes
        """
        query = select(LLMRequest).where(LLMRequest.user_id == user_id)
        # Utiliser desc() explicitement
        query = query.order_by(desc(LLMRequest.created_at))
        query = query.offset(offset).limit(limit)
        
        # Utiliser la session async pour exec
        result = await self.db_session.exec(query)
        return result.all()

    # Déplacer get_all_requests dans la classe et le rendre async
    async def get_all_requests(self, limit: int = 10, offset: int = 0) -> List[LLMRequest]:
        """
        Récupère toutes les requêtes LLM (pour admin, par exemple).
        
        Args:
            limit: Nombre maximum de requêtes à récupérer
            offset: Offset pour la pagination
            
        Returns:
            List[LLMRequest]: Liste des requêtes
        """
        query = select(LLMRequest)
        # Utiliser desc() explicitement
        query = query.order_by(desc(LLMRequest.created_at))
        query = query.offset(offset).limit(limit)
        
        result = await self.db_session.exec(query)
        return result.all() 