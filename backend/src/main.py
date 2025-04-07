import logging

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from typing import Optional, List, Annotated, Any, Dict, Tuple
from fastapi import FastAPI, HTTPException, Depends, status, Response, Body, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
import json
import random
from pydantic import BaseModel
from decimal import Decimal
from fastapi.staticfiles import StaticFiles

# --- Importer la configuration ---
from .core import config

# --- Importer les modèles SQLAlchemy DB ---
from .database import models

# --- Importer les Schémas Pydantic ---
# import schemas <-- Supprimé

# --- Importer les fonctions CRUD V3 --- (Fichier supprimé)
# import crud

# --- Importer logique LLM (sera adaptée plus tard) ---
# Suppression de l'import obsolète de llm_logic
# from llm_logic import get_llm, stock_prompt, general_chat_prompt, parsing_prompt

# --- Importer le service d'envoi d'email (inchangé pour l'instant) ---
# Suppression de l'import obsolète de services
# import services
# Suppression de l'import obsolète de pdf_utils
# import pdf_utils

# --- Importer les utilitaires d'authentification ---
# Rendre l'import relatif
from .core.security import get_current_admin_user_entity, get_current_active_user_entity, get_optional_current_active_user_entity
# Rendre l'import relatif
from .users.domain.user_entity import UserEntity

# --- Importer la dépendance de session DB ---
# Remplacer l'ancien import par le chemin correct
from .core.database import get_db_session, AsyncSession

# --- Importer les nouveaux routeurs ---
# Rendre les imports relatifs
from .users.interfaces.user_router import auth_router, user_router
from .addresses.interfaces.address_router import address_router
from .llm.interfaces.api import llm_router
from .products.interfaces.api import product_router, category_router, tags_router, stock_router
from .quotes.interfaces.api import quote_router
from .orders.interfaces.api import order_router



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
# Inclure les nouveaux routeurs
# ======================================================
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(address_router)
app.include_router(llm_router)
app.include_router(product_router)
app.include_router(category_router)
app.include_router(tags_router)
app.include_router(stock_router)
app.include_router(quote_router)
app.include_router(order_router)

# ======================================================
# Endpoints: Adresses Utilisateur (SUPPRIMÉS)
# ======================================================

# @app.post("/users/me/addresses", ...) # Supprimé
# async def add_user_address(...): # Supprimé
    # ...

# @app.get("/users/me/addresses", ...) # Supprimé
# async def get_my_addresses(...): # Supprimé
    # ...

# @app.put("/users/me/addresses/{address_id}/default", ...) # Supprimé
# async def set_my_default_address(...): # Supprimé
    # ...

# @app.put("/users/me/addresses/{address_id}", ...) # Supprimé
# async def update_my_address(...): # Supprimé
    # ...

# @app.delete("/users/me/addresses/{address_id}", ...) # Supprimé
# async def delete_my_address(...): # Supprimé
    # ...

# ======================================================
# Endpoints: Produits, Catégories, Tags (SUPPRIMÉS)
# ======================================================

# Supprimer ici les fonctions et décorateurs pour :
# - @app.get("/products", ...)
# - @app.get("/products/{product_id}", ...)
# - @app.put("/products/{product_id}", ...)
# - parse_react_admin_params (si plus utilisé ailleurs, sinon le déplacer dans un fichier utils)
# - @app.get("/categories", ...)
# - @app.get("/categories/{category_id}", ...)
# - @app.put("/categories/{category_id}", ...)
# - @app.post("/products", ...)
# - @app.post("/categories", ...)
# - @app.post("/products/{product_id}/variants", ...)

# ======================================================
# Endpoints: Devis (Quotes) (SUPPRIMÉS - Migrés vers quote_router)
# ======================================================

# Le code pour @app.post("/quotes", ...), @app.get("/quotes/{quote_id}", ...),
# @app.get("/users/me/quotes", ...), et @app.patch("/quotes/{quote_id}/status", ...)
# est maintenant supprimé de ce fichier.

# ======================================================
# Endpoints: Commandes (Orders) (SUPPRIMÉS - Migrés vers order_router)
# ======================================================

# Les anciens endpoints @app.post("/orders", ...), @app.get("/orders/{order_id}", ...),
# @app.get("/users/me/orders", ...), et @app.patch("/orders/{order_id}/status", ...)
# sont maintenant supprimés de ce fichier.

# ======================================================
# Initialisation & Lancement
# ======================================================

# Note: L'ancien endpoint /products_old a été supprimé car marqué deprecated et levait une erreur.

# Lancement (si exécuté directement, pour debug local)
# if __name__ == "__main__":
#     import uvicorn
#     logger.info("Démarrage du serveur Uvicorn pour le développement...")
#     uvicorn.run(app, host="0.0.0.0", port=8000)