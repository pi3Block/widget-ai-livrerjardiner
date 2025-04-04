from pydantic import BaseModel, EmailStr

# Modèle Pydantic pour les données de la requête /order
class OrderRequest(BaseModel):
    user_email: EmailStr # Utilise EmailStr pour validation automatique
    item: str
    quantity: int
    delivery_method: str
