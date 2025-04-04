import logging
import psycopg2
from psycopg2 import OperationalError, ProgrammingError
from psycopg2.pool import SimpleConnectionPool
from fastapi import HTTPException
import random
# --- Supprimer imports PDF --- 
# import os
# from datetime import datetime
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib.units import inch
# from reportlab.lib.pagesizes import letter
# from reportlab.lib import colors

# --- Importer la configuration DB --- 
import config
# --- Importer la fonction PDF depuis pdf_utils --- 
from pdf_utils import generate_quote_pdf

logger = logging.getLogger(__name__)

# --- Initialisation du Pool de Connexions DB --- 
DB_POOL = None
try:
    if not config.POSTGRES_PASSWORD:
        logger.critical("Mot de passe DB non défini, impossible d'initialiser le pool.")
        # Lever une erreur ou utiliser un indicateur pour empêcher les opérations DB
    else:
        DB_POOL = SimpleConnectionPool(
            minconn=1,  # Garder au moins 1 connexion ouverte
            maxconn=10, # Maximum 10 connexions simultanées (ajuster selon besoin)
            dbname=config.POSTGRES_DB,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD,
            host=config.POSTGRES_HOST if hasattr(config, 'POSTGRES_HOST') else 'localhost', # Utiliser localhost si non défini
            port=config.POSTGRES_PORT if hasattr(config, 'POSTGRES_PORT') else '5432'      # Utiliser 5432 si non défini
        )
        logger.info("Pool de connexions DB initialisé.")
except OperationalError as pool_init_error:
    logger.critical(f"Erreur critique lors de l'initialisation du pool DB: {pool_init_error}")
    DB_POOL = None # Assurer que le pool est None si l'init échoue

# ----- Fonctions CRUD -----

def check_stock(item: str) -> int:
    logger.debug(f"[CRUD] Vérification du stock pour l'article : {item}")
    if not DB_POOL:
        logger.error("[CRUD] Pool DB non initialisé, opération annulée.")
        raise HTTPException(status_code=503, detail=config.DB_CONNECT_ERROR_MSG if hasattr(config, 'DB_CONNECT_ERROR_MSG') else "Erreur connexion DB")
    
    conn = None
    try:
        conn = DB_POOL.getconn() # Obtenir une connexion du pool
        with conn.cursor() as cur:
            cur.execute("SELECT quantity FROM stock WHERE item=%s", (item,))
            result = cur.fetchone()
            stock = result[0] if result else 0
        logger.debug(f"[CRUD] Stock trouvé : {stock}")
        return stock
    except OperationalError as e: # Erreur pendant l'opération, pas forcément connexion initiale
        logger.error(f"[CRUD] Erreur opérationnelle DB dans check_stock : {str(e)}")
        raise HTTPException(status_code=503, detail=config.DB_CONNECT_ERROR_MSG if hasattr(config, 'DB_CONNECT_ERROR_MSG') else "Erreur connexion DB")
    except ProgrammingError as e:
        logger.error(f"[CRUD] Erreur SQL dans check_stock : {str(e)}")
        raise HTTPException(status_code=500, detail=config.DB_SQL_ERROR_MSG if hasattr(config, 'DB_SQL_ERROR_MSG') else "Erreur SQL")
    except Exception as e:
        logger.error(f"[CRUD] Erreur inattendue dans check_stock : {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la vérification du stock.")
    finally:
        if conn:
            DB_POOL.putconn(conn) # Remettre la connexion dans le pool
            logger.debug("[CRUD] Connexion DB retournée au pool dans check_stock")

def save_quote(user_email: str, item: str, quantity: int) -> int:
    logger.debug(f"[CRUD] Sauvegarde du devis pour {user_email}, item={item}, quantity={quantity}")
    if not DB_POOL: # Vérifier pool
        # ... (gestion erreur pool non initialisé)
        raise HTTPException(status_code=503, detail=...) 

    unit_price = 5.0
    total_price = unit_price * quantity
    conn = None
    try:
        conn = DB_POOL.getconn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO quotes (user_email, item, quantity, unit_price, total_price) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (user_email, item, quantity, unit_price, total_price)
            )
            quote_id = cur.fetchone()[0]
            pdf_path = generate_quote_pdf(item, quantity, unit_price, total_price, quote_id)
            cur.execute("UPDATE quotes SET pdf_path=%s WHERE id=%s", (pdf_path, quote_id))
            conn.commit() # Commit après toutes les opérations réussies
        logger.debug(f"[CRUD] Devis sauvegardé : quote_id={quote_id}")
        return quote_id
    except Exception as e:
        if conn: conn.rollback() # Rollback en cas d'erreur (important!)
        logger.error(f"[CRUD] Erreur dans save_quote : {str(e)}", exc_info=True)
        # Lever l'exception appropriée (OperationalError -> 503, ProgrammingError -> 500, autre -> 500)
        if isinstance(e, OperationalError):
             raise HTTPException(status_code=503, detail=config.DB_CONNECT_ERROR_MSG if hasattr(config, 'DB_CONNECT_ERROR_MSG') else "Erreur connexion DB")
        elif isinstance(e, ProgrammingError):
             raise HTTPException(status_code=500, detail=config.DB_SQL_ERROR_MSG if hasattr(config, 'DB_SQL_ERROR_MSG') else "Erreur SQL")
        else:
             # Peut-être une erreur de generate_pdf ou autre
             raise HTTPException(status_code=500, detail=f"Erreur lors de la création du devis: {e}")
    finally:
        if conn:
            DB_POOL.putconn(conn)
            logger.debug("[CRUD] Connexion DB retournée au pool dans save_quote")

def save_pending_order(user_email: str, item: str, quantity: int):
    logger.debug(f"[CRUD] Sauvegarde commande en attente pour {user_email}...")
    conn = None
    try:
        if not config.POSTGRES_PASSWORD:
             raise OperationalError("Mot de passe base de données non configuré.")
        conn = DB_POOL.getconn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO pending_orders (user_email, item, quantity) VALUES (%s, %s, %s)",
                (user_email, item, quantity)
            )
            conn.commit()
            logger.debug("[CRUD] Commande en attente sauvegardée")
    except OperationalError as e:
        logger.error(f"[CRUD] Erreur opérationnelle DB dans save_pending_order : {str(e)}")
        raise HTTPException(status_code=503, detail=config.DB_CONNECT_ERROR_MSG if hasattr(config, 'DB_CONNECT_ERROR_MSG') else "Erreur connexion DB")
    except ProgrammingError as e:
        logger.error(f"[CRUD] Erreur SQL dans save_pending_order : {str(e)}")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=config.DB_SQL_ERROR_MSG if hasattr(config, 'DB_SQL_ERROR_MSG') else "Erreur SQL")
    except Exception as e:
        logger.error(f"[CRUD] Erreur inattendue save_pending_order : {str(e)}", exc_info=True)
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="Erreur sauvegarde commande en attente.")
    finally:
        if conn:
            DB_POOL.putconn(conn)
            logger.debug("[CRUD] Connexion DB retournée au pool dans save_pending_order")

def save_order(user_email: str, item: str, quantity: int, delivery_method: str):
    logger.debug(f"[CRUD] Sauvegarde de la commande pour {user_email}...")
    conn = None
    try:
        if not config.POSTGRES_PASSWORD:
             raise OperationalError("Mot de passe base de données non configuré.")
        conn = DB_POOL.getconn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (user_email, item, quantity, delivery_method) VALUES (%s, %s, %s, %s)",
                (user_email, item, quantity, delivery_method)
            )
            cur.execute("UPDATE stock SET quantity = quantity - %s WHERE item=%s", (quantity, item))
            # TODO: Vérifier si la mise à jour du stock a réussi
            conn.commit()
            logger.debug("[CRUD] Commande sauvegardée et stock mis à jour")
    except OperationalError as e:
        logger.error(f"[CRUD] Erreur opérationnelle DB dans save_order : {str(e)}")
        raise HTTPException(status_code=503, detail=config.DB_CONNECT_ERROR_MSG if hasattr(config, 'DB_CONNECT_ERROR_MSG') else "Erreur connexion DB")
    except ProgrammingError as e:
        logger.error(f"[CRUD] Erreur SQL dans save_order : {str(e)}")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=config.DB_SQL_ERROR_MSG if hasattr(config, 'DB_SQL_ERROR_MSG') else "Erreur SQL")
    except Exception as e:
        logger.error(f"[CRUD] Erreur inattendue dans save_order : {str(e)}", exc_info=True)
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="Erreur finalisation commande.")
    finally:
        if conn:
            DB_POOL.putconn(conn)
            logger.debug("[CRUD] Connexion DB retournée au pool dans save_order")
