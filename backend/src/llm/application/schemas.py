from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# DTO pour représenter un item extrait du parsing
class RequestedItem(BaseModel):
    sku: Optional[str] = None
    base_product: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    quantity: int = 1

# DTO pour représenter le résultat du parsing d'intention
class ParsedIntent(BaseModel):
    intent: str = "info_generale"
    items: List[RequestedItem] = Field(default_factory=list)

# DTO pour la logique interne du service de chat (si nécessaire)
# Par exemple, pour passer des informations entre les étapes
class ChatContext(BaseModel):
    user_input: str
    selected_model: str
    user_id: Optional[int | str] = None # ID numérique ou "Anonyme"
    parsed_intent: ParsedIntent
    # Ajouter d'autres champs si besoin (ex: stock_summary)
    stock_summary: Optional[str] = None
