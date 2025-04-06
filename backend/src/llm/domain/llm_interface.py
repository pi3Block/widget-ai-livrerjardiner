import abc
from typing import Any, Dict

class AbstractLLM(abc.ABC):
    """Interface abstraite pour un client Large Language Model."""

    @abc.abstractmethod
    async def invoke(self, prompt: str, config: Dict[str, Any] = None) -> str:
        """
        Invoque le LLM avec un prompt donné et retourne la réponse textuelle.

        Args:
            prompt: Le texte d'entrée pour le LLM.
            config: Configuration optionnelle pour l'invocation (peut inclure max_tokens, temperature, etc.)

        Returns:
            La réponse textuelle générée par le LLM.
        """
        raise NotImplementedError
    
    # On pourrait ajouter d'autres méthodes si nécessaire, par exemple pour le streaming
    # @abc.abstractmethod
    # async def stream(self, prompt: str, config: Dict[str, Any] = None) -> AsyncIterator[str]:
    #     raise NotImplementedError
