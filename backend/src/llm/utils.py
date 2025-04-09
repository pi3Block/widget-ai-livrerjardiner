"""
Utilitaires pour le module LLM.
"""
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.llm.constants import (
    MAX_PROMPT_LENGTH,
    MAX_RESPONSE_LENGTH,
    REQUEST_STATUS_PENDING,
    REQUEST_STATUS_PROCESSING,
    REQUEST_STATUS_COMPLETED,
    REQUEST_STATUS_FAILED
)

def validate_prompt(prompt: str) -> bool:
    """
    Valide un prompt pour le LLM.
    
    Args:
        prompt: Le prompt à valider
        
    Returns:
        bool: True si le prompt est valide, False sinon
    """
    if not prompt or not isinstance(prompt, str):
        return False
    
    return len(prompt) <= MAX_PROMPT_LENGTH

def format_llm_request_reference(request_id: int, timestamp: Optional[datetime] = None) -> str:
    """
    Génère une référence unique pour une requête LLM.
    
    Args:
        request_id: ID de la requête
        timestamp: Horodatage (optionnel)
        
    Returns:
        str: Référence formatée
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    return f"LLM-{request_id:06d}-{timestamp.strftime('%Y%m%d%H%M%S')}"

def calculate_tokens(text: str) -> int:
    """
    Calcule une estimation du nombre de tokens dans un texte.
    Cette fonction est une approximation simple.
    
    Args:
        text: Le texte à analyser
        
    Returns:
        int: Nombre estimé de tokens
    """
    # Approximation simple: 1 token ≈ 4 caractères
    return len(text) // 4

def format_chat_messages(prompt: str, system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Formate les messages pour une requête de chat.
    
    Args:
        prompt: Le prompt utilisateur
        system_prompt: Le prompt système (optionnel)
        
    Returns:
        List[Dict[str, str]]: Liste de messages formatés
    """
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": prompt})
    
    return messages

def measure_execution_time(func):
    """
    Décorateur pour mesurer le temps d'exécution d'une fonction.
    
    Args:
        func: La fonction à décorer
        
    Returns:
        function: La fonction décorée
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Ajouter le temps d'exécution au résultat si c'est un dictionnaire
        if isinstance(result, dict):
            result["execution_time"] = execution_time
        
        return result
    
    return wrapper 