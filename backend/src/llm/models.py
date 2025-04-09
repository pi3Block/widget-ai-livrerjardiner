"""
Modèles et schémas pour le module LLM.

Ce module contient tous les modèles de données utilisés dans le module LLM,
y compris les modèles SQLModel pour la persistance et les schémas Pydantic
pour la validation et le transfert de données.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlmodel import SQLModel, Field
from pydantic import BaseModel
from sqlalchemy import JSON

# --- Modèles SQLModel pour la persistance ---

class LLMRequestBase(SQLModel):
    """Modèle de base pour les requêtes LLM."""
    prompt: str = Field(description="Le prompt à envoyer au modèle LLM")
    model: str = Field(default="gpt-3.5-turbo", description="Le modèle LLM à utiliser")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Température pour la génération")
    max_tokens: Optional[int] = Field(default=None, description="Nombre maximum de tokens à générer")
    system_prompt: Optional[str] = Field(default=None, description="Prompt système pour guider le modèle")
    llm_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON, description="Métadonnées supplémentaires")

class LLMRequest(LLMRequestBase, table=True):
    """Modèle de table pour les requêtes LLM."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="pending")
    response: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)
    tokens_used: Optional[int] = Field(default=None)
    processing_time: Optional[float] = Field(default=None)
    llm_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)

class LLMResponseBase(SQLModel):
    """Modèle de base pour les réponses LLM."""
    content: str = Field(description="Contenu de la réponse")
    model: str = Field(description="Modèle utilisé")
    tokens_used: int = Field(description="Nombre de tokens utilisés")
    processing_time: float = Field(description="Temps de traitement en secondes")

class LLMResponse(LLMResponseBase):
    """Modèle pour les réponses LLM."""
    id: int
    request_id: int
    created_at: datetime 

# --- Schémas Pydantic pour la validation et le transfert de données ---

class RequestedItem(BaseModel):
    """Schéma pour représenter un item extrait du parsing."""
    sku: Optional[str] = None
    base_product: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    quantity: int = 1

class ParsedIntent(BaseModel):
    """Schéma pour représenter le résultat du parsing d'intention."""
    intent: str = "info_generale"
    items: List[RequestedItem] = Field(default_factory=list)

class ChatContext(BaseModel):
    """Schéma pour la logique interne du service de chat."""
    user_input: str
    selected_model: str
    user_id: Optional[int | str] = None  # ID numérique ou "Anonyme"
    parsed_intent: ParsedIntent
    # Ajouter d'autres champs si besoin (ex: stock_summary)
    stock_summary: Optional[str] = None 