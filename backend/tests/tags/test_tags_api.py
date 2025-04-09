import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from src.main import app # Importer l'application FastAPI
from src.database import get_db_session
from src.auth.security import get_current_admin_user # Importer la dépendance d'admin
from src.users.models import User, UserRead # Importer les modèles User pour l'override
from src.tags.models import TagRead # Importer le schéma de réponse

# Utiliser une DB SQLite en mémoire pour les tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_tags.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=True, future=True)

# Session asynchrone pour les tests
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession, expire_on_commit=False
)

# Fixture pour initialiser la base de données avant les tests du module
@pytest_asyncio.fixture(scope="module", autouse=True)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    # Nettoyer la DB après les tests du module (optionnel si en mémoire et recréée)
    # async with engine.begin() as conn:
    #     await conn.run_sync(SQLModel.metadata.drop_all)

# Fixture pour fournir une session de test
@pytest_asyncio.fixture(scope="function") # Nouvelle session par test
async def db_session() -> get_db_session:
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback() # Assurer que les transactions sont annulées après chaque test

# Fixture pour mocker l'utilisateur admin
@pytest.fixture(scope="module")
def mock_admin_user() -> UserRead:
    # Créer un utilisateur admin factice pour les tests
    # Note: Ne pas utiliser de mot de passe réel ou sensible ici
    return UserRead(id=999, email="admin@test.com", name="Admin Test", is_admin=True)

# Fixture pour le client HTTP asynchrone
@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession, mock_admin_user: UserRead) -> AsyncClient:

    # Fonction pour overrider la dépendance get_async_session
    async def override_get_async_session():
        yield db_session

    # Fonction pour overrider la dépendance get_current_admin_user
    async def override_get_current_admin_user():
        return mock_admin_user

    # Appliquer les overrides sur l'application FastAPI
    app.dependency_overrides[get_async_session] = override_get_async_session
    app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Nettoyer les overrides après les tests pour éviter les fuites
    app.dependency_overrides.clear()

TAGS_API_PREFIX = "/api/v1/tags" # Préfixe de l'API tel que défini dans main.py

@pytest.mark.asyncio
async def test_create_tag_success(async_client: AsyncClient):
    """Teste la création réussie d'un tag."""
    tag_name = "Nouveau Tag"
    response = await async_client.post(TAGS_API_PREFIX + "/", json={"name": tag_name})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == tag_name
    assert "id" in data

@pytest.mark.asyncio
async def test_create_tag_duplicate(async_client: AsyncClient):
    """Teste la création d'un tag avec un nom dupliqué."""
    tag_name = "Tag Dupliqué"
    # Créer le premier tag
    response1 = await async_client.post(TAGS_API_PREFIX + "/", json={"name": tag_name})
    assert response1.status_code == 201
    # Tenter de créer le deuxième tag avec le même nom
    response2 = await async_client.post(TAGS_API_PREFIX + "/", json={"name": tag_name})
    assert response2.status_code == 409 # Conflit

@pytest.mark.asyncio
async def test_list_tags(async_client: AsyncClient):
    """Teste la récupération de la liste des tags."""
    # Créer quelques tags
    await async_client.post(TAGS_API_PREFIX + "/", json={"name": "Tag A"})
    await async_client.post(TAGS_API_PREFIX + "/", json={"name": "Tag B"})

    response = await async_client.get(TAGS_API_PREFIX + "/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Vérifier que les tags créés sont présents (l'ordre n'est pas garanti sans tri)
    tag_names_in_response = {tag['name'] for tag in data}
    assert "Tag A" in tag_names_in_response
    assert "Tag B" in tag_names_in_response
    # Le test précédent a aussi créé "Nouveau Tag" et "Tag Dupliqué"
    assert "Nouveau Tag" in tag_names_in_response
    assert "Tag Dupliqué" in tag_names_in_response

@pytest.mark.asyncio
async def test_get_tag_success(async_client: AsyncClient):
    """Teste la récupération d'un tag spécifique par ID."""
    tag_name = "Tag à Récupérer"
    create_response = await async_client.post(TAGS_API_PREFIX + "/", json={"name": tag_name})
    assert create_response.status_code == 201
    tag_id = create_response.json()["id"]

    response = await async_client.get(f"{TAGS_API_PREFIX}/{tag_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tag_id
    assert data["name"] == tag_name

@pytest.mark.asyncio
async def test_get_tag_not_found(async_client: AsyncClient):
    """Teste la récupération d'un tag inexistant."""
    response = await async_client.get(f"{TAGS_API_PREFIX}/99999") # ID non existant
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_tag_success(async_client: AsyncClient):
    """Teste la mise à jour réussie d'un tag."""
    tag_name_initial = "Tag à Mettre à Jour"
    new_tag_name = "Tag Mis à Jour"
    create_response = await async_client.post(TAGS_API_PREFIX + "/", json={"name": tag_name_initial})
    assert create_response.status_code == 201
    tag_id = create_response.json()["id"]

    update_response = await async_client.put(f"{TAGS_API_PREFIX}/{tag_id}", json={"name": new_tag_name})
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["id"] == tag_id
    assert data["name"] == new_tag_name

    # Vérifier que la récupération retourne le nom mis à jour
    get_response = await async_client.get(f"{TAGS_API_PREFIX}/{tag_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == new_tag_name

@pytest.mark.asyncio
async def test_update_tag_duplicate_name(async_client: AsyncClient):
    """Teste la mise à jour d'un tag vers un nom déjà existant."""
    tag_name_1 = "Nom Existant 1"
    tag_name_2 = "Nom Existant 2"
    await async_client.post(TAGS_API_PREFIX + "/", json={"name": tag_name_1})
    response_tag2 = await async_client.post(TAGS_API_PREFIX + "/", json={"name": tag_name_2})
    tag2_id = response_tag2.json()["id"]

    # Tenter de renommer tag 2 avec le nom de tag 1
    update_response = await async_client.put(f"{TAGS_API_PREFIX}/{tag2_id}", json={"name": tag_name_1})
    assert update_response.status_code == 409 # Conflit

@pytest.mark.asyncio
async def test_update_tag_not_found(async_client: AsyncClient):
    """Teste la mise à jour d'un tag inexistant."""
    response = await async_client.put(f"{TAGS_API_PREFIX}/99999", json={"name": "Nouveau Nom Inexistant"})
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_tag_success(async_client: AsyncClient):
    """Teste la suppression réussie d'un tag."""
    tag_name = "Tag à Supprimer"
    create_response = await async_client.post(TAGS_API_PREFIX + "/", json={"name": tag_name})
    assert create_response.status_code == 201
    tag_id = create_response.json()["id"]

    delete_response = await async_client.delete(f"{TAGS_API_PREFIX}/{tag_id}")
    assert delete_response.status_code == 204

    # Vérifier que la récupération échoue (Not Found)
    get_response = await async_client.get(f"{TAGS_API_PREFIX}/{tag_id}")
    assert get_response.status_code == 404

@pytest.mark.asyncio
async def test_delete_tag_not_found(async_client: AsyncClient):
    """Teste la suppression d'un tag inexistant."""
    response = await async_client.delete(f"{TAGS_API_PREFIX}/99999")
    assert response.status_code == 404

# Ajouter des tests pour les accès non autorisés (sans mocker l'admin)
# Vous auriez besoin d'une fixture client séparée sans l'override d'authentification

# Exemple (nécessite une fixture `unauthenticated_client`):
# @pytest.mark.asyncio
# async def test_create_tag_unauthorized(unauthenticated_client: AsyncClient):
#     response = await unauthenticated_client.post(TAGS_API_PREFIX + "/", json={"name": "Tag Non Autorisé"})
#     assert response.status_code == 401 # Unauthorized 