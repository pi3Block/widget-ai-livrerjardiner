"""Exceptions spécifiques au domaine LLM."""

class LLMBaseException(Exception):
    """Classe de base pour les exceptions liées au LLM."""
    pass

class LLMInitializationError(LLMBaseException):
    """Levée lorsque l'initialisation du client LLM échoue."""
    def __init__(self, message: str = "Erreur lors de l'initialisation du client LLM.", original_exception: Exception = None):
        super().__init__(message)
        self.original_exception = original_exception

class LLMInvocationError(LLMBaseException):
    """Levée lorsqu'une erreur se produit pendant l'invocation du LLM."""
    def __init__(self, message: str = "Erreur lors de l'invocation du LLM.", original_exception: Exception = None):
        super().__init__(message)
        self.original_exception = original_exception

class LLMParsingError(LLMBaseException):
    """Levée lorsque le parsing de la réponse LLM échoue."""
    def __init__(self, message: str = "Erreur lors du parsing de la réponse LLM.", raw_output: str = None):
        super().__init__(message)
        self.raw_output = raw_output
