"""
Module principal de l'application FastAPI LivrerJardiner.

Ce module configure et initialise l'instance FastAPI, ajoute les middlewares nécessaires (CORS),
monte les fichiers statiques, et inclut les routeurs pour les différentes fonctionnalités
de l'API (authentification, utilisateurs, produits, commandes, etc.).
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


# --- Importer les routeurs ---
# Utilisation d'imports relatifs standardisés pour tous les modules internes
from src.auth.router import auth_router
from src.users.router import user_router
from src.addresses.router import router as address_router
from src.llm.router import router as llm_router
from src.products.router import product_router
from src.categories.router import router as categories_router
from src.product_variants.router import variant_router
from src.tags.router import tag_router
from src.quotes.router import quote_router
from src.orders.router import order_router
from src.stock.router import router as stock_router
from src.stock_movements.router import router as stock_movement_router

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LivrerJardiner API",
    description="API pour la gestion des produits, commandes, utilisateurs et interactions IA.",
    version="1.1.0" # Version avec SQLAlchemy + FastCRUD
)

# Configurer CORS (Mise à jour)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://livrerjardiner.fr",
        "https://cdn.jsdelivr.net",
        "https://pierrelegrand.fr",
        "http://localhost:3000",
        "https://pi3block.github.io",
        "http://localhost:5173", 
        "http://localhost:4000",      
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range"],
)

# Montage des fichiers statiques (si nécessaire)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ======================================================
# Inclure les routeurs
# ======================================================
# Routeurs d'authentification et d'utilisateurs
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentification"])
app.include_router(user_router, prefix="/api/v1/users", tags=["Utilisateurs"])

# Routeur d'adresses
app.include_router(address_router, prefix="/api/v1/addresses", tags=["Addresses"])

# Routeurs de produits, catégories, variations, tags
app.include_router(product_router, prefix="/api/v1/products", tags=["Produits"])
app.include_router(categories_router, prefix="/api/v1/categories", tags=["Categories"])
app.include_router(variant_router, prefix="/api/v1/product-variants", tags=["Product Variants"])
app.include_router(tag_router, prefix="/api/v1/tags", tags=["Tags"])

# Routeurs de devis et commandes
app.include_router(quote_router, prefix="/api/v1/quotes", tags=["Quotes"])
app.include_router(order_router, prefix="/api/v1/orders", tags=["Orders"])

# Routeur LLM
app.include_router(llm_router, prefix="/api/v1/llm", tags=["LLM"])

# Routeur de stock et mouvements
app.include_router(stock_router, prefix="/api/v1/stock", tags=["Stock"])
app.include_router(stock_movement_router, prefix="/api/v1/stock-movements", tags=["Stock Movements"])
