"""
Tests d'intégration pour les endpoints de l'API du module Utilisateur.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Importer les modèles et schémas nécessaires
from src.users.models import User, UserCreate, UserUpdate, UserRead
from src.core.config import settings # Pour le préfixe API

# Le préfixe API global pour construire les URLs
API_PREFIX = settings.API_V1_PREFIX

pytestmark = pytest.mark.asyncio

# --- Tests pour la Création d'Utilisateurs (POST /users/) ---

async def test_create_user_success_admin(
    test_client: AsyncClient,
    auth_headers_admin: dict[str, str] # Utilise l'admin
):
    """Teste la création réussie d'un utilisateur par un administrateur."""
    user_data = {
        "email": "newuser@example.com",
        "password": "newpassword123",
        "name": "New User",
        "is_admin": False
    }
    response = await test_client.post(
        f"{API_PREFIX}/users/",
        json=user_data,
        headers=auth_headers_admin
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]
    assert data["is_admin"] == user_data["is_admin"]
    assert "id" in data
    # Vérifier que le mot de passe n'est pas retourné
    assert "password" not in data
    assert "password_hash" not in data

async def test_create_user_forbidden_standard_user(
    test_client: AsyncClient,
    auth_headers_user: dict[str, str] # Utilise l'utilisateur standard
):
    """Teste que la création d'utilisateur est interdite pour un utilisateur standard."""
    user_data = {
        "email": "anotheruser@example.com",
        "password": "password123",
        "name": "Another User"
    }
    response = await test_client.post(
        f"{API_PREFIX}/users/",
        json=user_data,
        headers=auth_headers_user
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

async def test_create_user_duplicate_email(
    test_client: AsyncClient,
    auth_headers_admin: dict[str, str],
    admin_user: User # Pour obtenir l'email de l'admin existant
):
    """Teste l'échec de la création d'un utilisateur avec un email déjà existant."""
    user_data = {
        "email": admin_user.email, # Email déjà utilisé par l'admin
        "password": "newpassword123",
        "name": "Duplicate User"
    }
    response = await test_client.post(
        f"{API_PREFIX}/users/",
        json=user_data,
        headers=auth_headers_admin
    )
    # Le service devrait retourner 400 pour un email dupliqué
    assert response.status_code == status.HTTP_400_BAD_REQUEST

async def test_create_user_unauthenticated(test_client: AsyncClient):
    """Teste que la création d'utilisateur échoue sans authentification."""
    user_data = {"email": "unauth@example.com", "password": "password"}
    response = await test_client.post(f"{API_PREFIX}/users/", json=user_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

# --- Tests pour la Lecture des Utilisateurs (GET /users/ et GET /users/me) ---

async def test_get_users_list_success_admin(
    test_client: AsyncClient,
    auth_headers_admin: dict[str, str],
    admin_user: User,
    test_user: User # S'assurer qu'il y a au moins deux utilisateurs
):
    """Teste la récupération de la liste des utilisateurs par un administrateur."""
    response = await test_client.get(f"{API_PREFIX}/users/", headers=auth_headers_admin)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    # Vérifier qu'on récupère au moins les deux utilisateurs créés par les fixtures
    assert len(data) >= 2
    emails = [user["email"] for user in data]
    assert admin_user.email in emails
    assert test_user.email in emails
    # Vérifier que le mot de passe n'est pas inclus
    if data:
        assert "password" not in data[0]
        assert "password_hash" not in data[0]

async def test_get_users_list_forbidden_standard_user(
    test_client: AsyncClient,
    auth_headers_user: dict[str, str]
):
    """Teste que la récupération de la liste des utilisateurs est interdite pour un utilisateur standard."""
    response = await test_client.get(f"{API_PREFIX}/users/", headers=auth_headers_user)
    assert response.status_code == status.HTTP_403_FORBIDDEN

async def test_get_users_list_unauthenticated(test_client: AsyncClient):
    """Teste que la récupération de la liste des utilisateurs échoue sans authentification."""
    response = await test_client.get(f"{API_PREFIX}/users/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

async def test_get_current_user_me_success(
    test_client: AsyncClient,
    auth_headers_user: dict[str, str],
    test_user: User
):
    """Teste la récupération des informations de l'utilisateur courant ('me')."""
    response = await test_client.get(f"{API_PREFIX}/users/me/", headers=auth_headers_user)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == test_user.email
    assert data["id"] == test_user.id
    assert data["name"] == test_user.name
    assert data["is_admin"] == test_user.is_admin
    assert "password" not in data
    assert "password_hash" not in data

async def test_get_current_user_me_unauthenticated(test_client: AsyncClient):
    """Teste que la récupération de 'me' échoue sans authentification."""
    response = await test_client.get(f"{API_PREFIX}/users/me/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

# --- Tests pour la Lecture d'un Utilisateur par ID (GET /users/{user_id}) ---

async def test_get_user_by_id_success_admin(
    test_client: AsyncClient,
    auth_headers_admin: dict[str, str],
    test_user: User # L'admin récupère l'utilisateur standard
):
    """Teste la récupération d'un utilisateur par ID par un administrateur."""
    response = await test_client.get(
        f"{API_PREFIX}/users/{test_user.id}",
        headers=auth_headers_admin
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email

async def test_get_user_by_id_forbidden_standard_user(
    test_client: AsyncClient,
    auth_headers_user: dict[str, str],
    admin_user: User # L'utilisateur standard essaie de récupérer l'admin
):
    """Teste que récupérer un autre utilisateur par ID est interdit pour un utilisateur standard."""
    response = await test_client.get(
        f"{API_PREFIX}/users/{admin_user.id}",
        headers=auth_headers_user
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

async def test_get_user_by_id_not_found(
    test_client: AsyncClient,
    auth_headers_admin: dict[str, str]
):
    """Teste la récupération d'un utilisateur inexistant par ID."""
    non_existent_id = 99999
    response = await test_client.get(
        f"{API_PREFIX}/users/{non_existent_id}",
        headers=auth_headers_admin
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

# --- Tests pour la Mise à Jour d'Utilisateurs (PUT /users/{user_id}) ---

async def test_update_user_success_admin(
    test_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict[str, str],
    test_user: User # L'admin met à jour l'utilisateur standard
):
    """Teste la mise à jour réussie d'un utilisateur par un administrateur."""
    update_data = {"name": "Updated Name", "is_admin": True}
    response = await test_client.put(
        f"{API_PREFIX}/users/{test_user.id}",
        json=update_data,
        headers=auth_headers_admin
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email # Email ne doit pas changer
    assert data["name"] == update_data["name"]
    assert data["is_admin"] == update_data["is_admin"]

    # Vérifier en base de données
    await db_session.refresh(test_user) # Recharger depuis la DB
    # Mettre à jour l'objet test_user localement pour refléter le changement avant l'assert
    test_user.name = update_data["name"]
    test_user.is_admin = update_data["is_admin"]
    
    user_in_db = await db_session.get(User, test_user.id)
    assert user_in_db is not None
    assert user_in_db.name == update_data["name"]
    assert user_in_db.is_admin == update_data["is_admin"]


async def test_update_user_forbidden_standard_user(
    test_client: AsyncClient,
    auth_headers_user: dict[str, str],
    admin_user: User # L'utilisateur standard essaie de mettre à jour l'admin
):
    """Teste que la mise à jour d'un autre utilisateur est interdite pour un utilisateur standard."""
    update_data = {"name": "Attempted Update"}
    response = await test_client.put(
        f"{API_PREFIX}/users/{admin_user.id}",
        json=update_data,
        headers=auth_headers_user
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

async def test_update_user_not_found(
    test_client: AsyncClient,
    auth_headers_admin: dict[str, str]
):
    """Teste la mise à jour d'un utilisateur inexistant."""
    non_existent_id = 99999
    update_data = {"name": "Ghost User"}
    response = await test_client.put(
        f"{API_PREFIX}/users/{non_existent_id}",
        json=update_data,
        headers=auth_headers_admin
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

# --- Tests pour la Suppression d'Utilisateurs (DELETE /users/{user_id}) ---

async def test_delete_user_success_admin(
    test_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_admin: dict[str, str],
    test_user_2: User # L'admin supprime le deuxième utilisateur standard
):
    """Teste la suppression réussie d'un utilisateur par un administrateur."""
    user_id_to_delete = test_user_2.id
    response = await test_client.delete(
        f"{API_PREFIX}/users/{user_id_to_delete}",
        headers=auth_headers_admin
    )
    assert response.status_code == status.HTTP_200_OK # ou 204 si pas de contenu retourné
    data = response.json()
    assert data["id"] == user_id_to_delete # Vérifier que l'ID de l'utilisateur supprimé est retourné

    # Vérifier en base de données
    user_in_db = await db_session.get(User, user_id_to_delete)
    assert user_in_db is None

async def test_delete_user_forbidden_standard_user(
    test_client: AsyncClient,
    auth_headers_user: dict[str, str],
    admin_user: User # L'utilisateur standard essaie de supprimer l'admin
):
    """Teste que la suppression d'un autre utilisateur est interdite pour un utilisateur standard."""
    response = await test_client.delete(
        f"{API_PREFIX}/users/{admin_user.id}",
        headers=auth_headers_user
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

async def test_delete_user_not_found(
    test_client: AsyncClient,
    auth_headers_admin: dict[str, str]
):
    """Teste la suppression d'un utilisateur inexistant."""
    non_existent_id = 99999
    response = await test_client.delete(
        f"{API_PREFIX}/users/{non_existent_id}",
        headers=auth_headers_admin
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

# TODO: Ajouter des tests pour les cas de validation (422 Unprocessable Entity)
# TODO: Ajouter des tests pour la pagination si elle est implémentée dans GET /users/ 