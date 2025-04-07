import logging

# Configurer le logging TOUT AU DEBUT
# Mettre le niveau souhaité (DEBUG pour voir tous les messages)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Maintenant les autres imports ---
from typing import Optional, List, Annotated, Any, Dict, Tuple
from fastapi import FastAPI, HTTPException, Depends, status, Response, Body, Query, Request
# ... (garder les autres imports tels quels) ...

# --- Importer la configuration ---
from .core import config

# ... (reste du fichier main.py) ...

app = FastAPI(
    title="LivrerJardiner API",
    description="API pour la gestion des produits, commandes, utilisateurs et interactions IA.",
)