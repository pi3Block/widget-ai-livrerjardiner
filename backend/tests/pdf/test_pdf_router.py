import pytest
from httpx import AsyncClient
import asyncio

# Mark all tests in this module to use pytest-asyncio
pytestmark = pytest.mark.asyncio

# --- Test POST /api/v1/pdfs/requests/ ---

async def test_create_pdf_request_success(test_client_with_mock_pdf: AsyncClient):
    """
    Test successful creation of a PDF request.
    Expects 202 Accepted and checks basic response structure.
    """
    client = test_client_with_mock_pdf # Rendre explicite pour la clarté
    request_payload = {
        "template_name": "test_template",
        "data": {"key": "value"},
        "options": {"orientation": "portrait"}
    }
    response = await client.post("/api/v1/pdfs/requests/", json=request_payload)

    assert response.status_code == 202 # Check for 202 Accepted
    response_data = response.json()

    assert "id" in response_data
    assert isinstance(response_data["id"], int)
    assert response_data["template_name"] == request_payload["template_name"]
    assert response_data["data"] == request_payload["data"]
    assert response_data["options"] == request_payload["options"]
    assert response_data["status"] == "pending" # Initial status
    assert response_data["file_path"] is None
    assert response_data["error"] is None
    assert "created_at" in response_data
    assert "user_id" in response_data # Should match placeholder or logged-in user in real tests

async def test_create_pdf_request_invalid_data(test_client_with_mock_pdf: AsyncClient):
    """
    Test request creation with invalid data (missing required field).
    Expects 422 Unprocessable Entity.
    """
    client = test_client_with_mock_pdf
    invalid_payload = {
        # Missing "template_name"
        "data": {"key": "value"}
    }
    response = await client.post("/api/v1/pdfs/requests/", json=invalid_payload)
    assert response.status_code == 422 # Unprocessable Entity

async def test_create_pdf_request_simulated_failure(test_client_with_mock_pdf: AsyncClient):
    client = test_client_with_mock_pdf
    request_payload = {
        "template_name": "fail_template", # Ce template déclenchera l'exception dans le mock
        "data": {"key": "value"}
    }
    # IMPORTANT: Comme la génération est en arrière-plan (status 202),
    # l'appel POST initial réussira toujours. L'échec simulé se produira
    # dans la tâche d'arrière-plan. Pour tester cela, il faudrait vérifier
    # le statut de la requête après un certain temps ou utiliser des mocks
    # plus avancés pour les BackgroundTasks.
    response = await client.post("/api/v1/pdfs/requests/", json=request_payload)
    assert response.status_code == 202
    request_id = response.json()["id"]

    # Attendre un peu (méthode simple mais peu fiable) ou utiliser des outils de test async
    await asyncio.sleep(0.1)

    # Vérifier que le statut est devenu "failed"
    get_response = await client.get(f"/api/v1/pdfs/requests/{request_id}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "failed"
    assert "Mock generation failed" in get_response.json()["error"]

# --- Test GET /api/v1/pdfs/requests/{request_id} ---

async def test_get_pdf_request_success(test_client_with_mock_pdf: AsyncClient):
    """
    Test retrieving an existing PDF request.
    """
    # 1. Create a request first
    client = test_client_with_mock_pdf
    create_payload = {"template_name": "get_test", "data": {}}
    create_response = await client.post("/api/v1/pdfs/requests/", json=create_payload)
    assert create_response.status_code == 202
    request_id = create_response.json()["id"]

    # 2. Try to retrieve it
    get_response = await client.get(f"/api/v1/pdfs/requests/{request_id}")
    assert get_response.status_code == 200
    response_data = get_response.json()

    assert response_data["id"] == request_id
    assert response_data["template_name"] == create_payload["template_name"]
    assert response_data["status"] == "pending" # Status might change if background task runs fast

async def test_get_pdf_request_not_found(test_client_with_mock_pdf: AsyncClient):
    """
    Test retrieving a non-existent PDF request.
    Expects 404 Not Found.
    """
    client = test_client_with_mock_pdf
    non_existent_id = 99999
    response = await client.get(f"/api/v1/pdfs/requests/{non_existent_id}")
    assert response.status_code == 404

# --- TODO: Add more tests ---
# - Test background task execution (might need generator mocking)
# - Test GET /api/v1/pdfs/{request_id} for download (if implemented)
# - Test DELETE /api/v1/pdfs/requests/{request_id} (if implemented)
# - Test LIST /api/v1/pdfs/requests/ (if implemented)
# - Test authentication/authorization if user_id is properly implemented
