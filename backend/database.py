import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import config # Pour récupérer les infos de connexion DB depuis config.py

logger = logging.getLogger(__name__)

# Vérifier que les variables de configuration nécessaires sont présentes
if not all([config.POSTGRES_USER, config.POSTGRES_PASSWORD, config.POSTGRES_DB]):
    logger.critical("Variables d'environnement DB manquantes (USER, PASSWORD, DB). Impossible de configurer SQLAlchemy.")
    # Gérer l'erreur (lever une exception, exit, etc.)
    # raise EnvironmentError("Missing database configuration variables.")
    # Pour l'instant, on logue et on continue, mais la connexion échouera.

DATABASE_URL = (
    f"postgresql+asyncpg://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}@"
    f"{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}"
)

try:
    # Création du moteur asynchrone
    async_engine = create_async_engine(
        DATABASE_URL,
        echo=config.DB_ECHO_LOG, # Afficher les requêtes SQL si True dans config
        pool_size=config.DB_POOL_SIZE, # Taille du pool (à définir dans config)
        max_overflow=config.DB_MAX_OVERFLOW # Connections supplémentaires (à définir dans config)
    )

    # Création d'une factory de sessions asynchrones
    # expire_on_commit=False permet d'accéder aux objets après commit (utile dans FastAPI)
    AsyncSessionFactory = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False, # Désactiver l'autoflush pour le mode async
    )

    # Base pour les modèles déclaratifs SQLAlchemy
    Base = declarative_base()

    logger.info("Moteur et Session Factory SQLAlchemy Async configurés.")

except Exception as e:
    logger.critical(f"Erreur lors de la configuration de SQLAlchemy Async: {e}", exc_info=True)
    async_engine = None
    AsyncSessionFactory = None
    Base = declarative_base() # Fournir une Base même en cas d'erreur pour éviter ImportError ailleurs
    # Gérer l'erreur de connexion initiale si nécessaire

# Fonction dépendance FastAPI pour obtenir une session DB
async def get_db_session() -> AsyncSession:
    """Dépendance FastAPI pour injecter une session DB asynchrone."""
    if AsyncSessionFactory is None:
        logger.error("La factory de session SQLAlchemy n'est pas initialisée.")
        raise RuntimeError("Database session factory is not initialized.")
        
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit() # Commit à la fin si tout s'est bien passé
        except Exception as e:
            logger.error(f"Erreur durant la session DB, rollback: {e}", exc_info=True)
            await session.rollback()
            # Propager l'exception pour que FastAPI la gère (ex: retourne 500)
            raise
        finally:
            # La session est automatiquement fermée par le context manager `async with`
            logger.debug("Session DB fermée.") 