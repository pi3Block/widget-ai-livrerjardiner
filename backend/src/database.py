import logging
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
# Importer SQLModel pour utiliser ses métadonnées
from sqlmodel import SQLModel

# Importer settings depuis config
from src.config import settings

logger = logging.getLogger(__name__)

# Charger les variables d'environnement depuis .env
load_dotenv()

# --- DEBUG: Afficher les composants avant de construire l'URL ------

# Récupérer l'URL de la base de données en utilisant les variables de config
DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@"
    f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

try:
    # Créer le moteur de base de données asynchrone
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.DB_ECHO_LOG, # Utiliser la variable de config pour echo
        future=True # Utilise l'API 2.0 de SQLAlchemy
    )

    # Créer une classe de session asynchrone
    AsyncSessionLocal = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False # Empêche les objets d'expirer après commit
    )

    # Base déclarative pour les modèles SQLAlchemy
    # Configurer pour utiliser les métadonnées de SQLModel
    Base = declarative_base(metadata=SQLModel.metadata)

    logger.info("Moteur et Session Factory SQLAlchemy Async configurés. Base utilise SQLModel.metadata.")

except Exception as e:
    logger.critical(f"Erreur lors de la configuration de SQLAlchemy Async: {e}", exc_info=True)
    engine = None
    AsyncSessionLocal = None
    Base = declarative_base(metadata=SQLModel.metadata) # Fournir une Base même en cas d'erreur pour éviter ImportError ailleurs
    # Gérer l'erreur de connexion initiale si nécessaire

# Fonction dépendance pour obtenir une session de base de données asynchrone
async def get_db_session() -> AsyncSession:
    """FastAPI dependency that provides an async database session."""
    if AsyncSessionLocal is None:
        logger.error("La factory de session SQLAlchemy n'est pas initialisée.")
        raise RuntimeError("Database session factory is not initialized.")
        
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Aucun commit explicite ici, car le commit devrait être géré
            # dans la logique métier (services) pour contrôler les transactions.
            # await session.commit() # Commenté intentionnellement
        except Exception as e:
            logger.error(f"Erreur durant la session DB, rollback: {e}", exc_info=True)
            await session.rollback()
            # Propager l'exception pour que FastAPI la gère (ex: retourne 500)
            raise
        finally:
            # Fermer la session à la fin de la requête.
            await session.close()
            logger.debug("Session DB fermée.")

# --- Fonctions utilitaires pour les tests (optionnel) ---
async def create_tables():
    """Crée toutes les tables définies (SQLModel et SQLAlchemy Base)."""
    async with engine.begin() as conn:
        # N'appeler que create_all sur les métadonnées partagées
        await conn.run_sync(SQLModel.metadata.create_all)

async def drop_tables():
    """Supprime toutes les tables définies (SQLModel et SQLAlchemy Base)."""
    async with engine.begin() as conn:
        # N'appeler que drop_all sur les métadonnées partagées
        await conn.run_sync(SQLModel.metadata.drop_all)

# Note sur les commits:
# Le commit explicite a été retiré de get_db_session.
# Il est préférable de gérer les commits au niveau des services applicatifs
# pour avoir un contrôle plus fin sur les transactions atomiques.
# Par exemple, dans un OrderService, vous feriez session.commit() 
# après avoir créé la commande ET décrémenté le stock avec succès. 
