import logging
from typing import Optional, Dict, Any
from langchain_community.llms import Ollama
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler

# Import de l'interface domaine
from ..domain.llm_interface import AbstractLLM
from ..domain.exceptions import LLMInitializationError, LLMInvocationError

# Import de la configuration
# Assurez-vous que le chemin est correct
from ...core import config

logger = logging.getLogger(__name__)

class OllamaClient(AbstractLLM):
    """Implémentation du client LLM utilisant Ollama."""

    # Utiliser un cache simple pour les instances initialisées
    _initialized_llms: Dict[str, Ollama] = {}
    _initialized: bool = False

    def __init__(self, model_name: str = "mistral"):
        # L'initialisation réelle est faite une seule fois via _ensure_initialized
        self.default_model_name = "mistral"
        self.requested_model_name = model_name
        OllamaClient._ensure_initialized()
        self.llm_instance = self._get_llm_instance(self.requested_model_name)

    @classmethod
    def _ensure_initialized(cls):
        """Initialise les modèles configurés si ce n'est pas déjà fait."""
        if not cls._initialized:
            logger.info("Initialisation des clients Ollama...")
            # Initialiser Mistral (modèle par défaut)
            mistral_instance = cls._initialize_single_llm("mistral")
            if mistral_instance:
                cls._initialized_llms["mistral"] = mistral_instance
            
            # Initialiser le modèle Meta si configuré
            if config.META_MODEL_NAME:
                 meta_instance = cls._initialize_single_llm(config.META_MODEL_NAME)
                 if meta_instance:
                     cls._initialized_llms[config.META_MODEL_NAME] = meta_instance
            
            cls._initialized = True
            logger.info(f"Clients Ollama initialisés: {list(cls._initialized_llms.keys())}")

    @classmethod
    def _initialize_single_llm(cls, model_name: str) -> Optional[Ollama]:
        """Tente d'initialiser un seul modèle LLM via Ollama."""
        try:
            llm = Ollama(model=model_name, base_url=config.OLLAMA_BASE_URL)
            # On pourrait ajouter un test d'invocation ici si nécessaire
            logger.info(f"Ollama LLM '{model_name}' initialisé depuis {config.OLLAMA_BASE_URL}")
            return llm
        except Exception as e:
            logger.error(f"Erreur initialisation Ollama LLM '{model_name}': {e}", exc_info=True)
            return None

    def _get_llm_instance(self, model_name: str) -> Optional[Ollama]:
        """Retourne l'instance LLM demandée, avec fallback."""
        # Gérer l'alias "meta"
        if model_name.lower() == "meta":
            model_name = config.META_MODEL_NAME

        selected_llm = self._initialized_llms.get(model_name)
        if selected_llm:
            logger.debug(f"Utilisation du modèle Ollama: {model_name}")
            return selected_llm
        
        # Fallback sur mistral
        fallback_llm = self._initialized_llms.get(self.default_model_name)
        if fallback_llm:
            logger.warning(f"Modèle Ollama '{model_name}' non disponible, fallback sur '{self.default_model_name}'.")
            return fallback_llm
            
        logger.error(f"Aucun modèle Ollama disponible (ni '{model_name}', ni '{self.default_model_name}').")
        return None

    async def invoke(self, prompt: str, config: Dict[str, Any] = None) -> str:
        """Invoque le modèle Ollama sélectionné."""
        if not self.llm_instance:
             logger.error("Tentative d'invocation LLM mais aucune instance n'est disponible.")
             # Lever une exception spécifique serait mieux
             raise RuntimeError("LLM non disponible") 
        
        # TODO: Intégrer la config (max_tokens, etc.) si l'API langchain le permet facilement
        # pour OllamaLLM().invoke ou .ainvoke
        try:
            logger.debug(f"Invocation asynchrone du modèle Ollama ({self.llm_instance.model})...")
            # Utiliser ainvoke pour l'asynchronisme
            response = await self.llm_instance.ainvoke(prompt)
            logger.debug("Invocation LLM terminée.")
            # La réponse de ainvoke est directement le string
            return response.strip() if isinstance(response, str) else str(response).strip()
        except Exception as e:
            logger.error(f"Erreur lors de l'invocation Ollama LLM ({self.llm_instance.model}): {e}", exc_info=True)
            # Lever une exception spécifique
            raise ConnectionError(f"Erreur communication avec LLM: {e}") 