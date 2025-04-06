from pydantic import BaseModel, EmailStr, Field, Json, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime
from decimal import Decimal # Pour les prix

# ======================================================
# Configuration Commune Pydantic
# ======================================================

# Configuration commune pour activer le mode ORM (from_attributes)
class OrmBaseModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True # Remplace orm_mode
    )