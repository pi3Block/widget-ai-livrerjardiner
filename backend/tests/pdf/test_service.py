"""
Tests pour le service PDF.
"""
import pytest
from datetime import datetime
from typing import Dict, Any

from src.pdf.models import PDFRequest, PDFRequestBase, PDFRequestCreate
from src.pdf.service import PDFService
from src.pdf.exceptions import PDFGenerationException, TemplateNotFoundException

@pytest.mark.asyncio
async def test_create_request(db_session):
    """Test la création d'une requête PDF."""
    service = PDFService(db_session)
    request_data = PDFRequestCreate(
        template_name="test_template",
        data={"key": "value"},
        options={"option1": "value1"}
    )
    
    request = await service.create_request(request_data, user_id=1)
    assert request.template_name == "test_template"
    assert request.data == {"key": "value"}
    assert request.options == {"option1": "value1"}
    assert request.user_id == 1
    assert request.status == "pending"
    assert request.created_at is not None

@pytest.mark.asyncio
async def test_get_request(db_session):
    """Test la récupération d'une requête PDF."""
    service = PDFService(db_session)
    
    # Créer une requête
    request_data = PDFRequestCreate(
        template_name="test_template",
        data={"key": "value"}
    )
    created_request = await service.create_request(request_data, user_id=1)
    
    # Récupérer la requête
    request = await service.get_request(created_request.id)
    assert request is not None
    assert request.id == created_request.id
    assert request.template_name == "test_template"

@pytest.mark.asyncio
async def test_get_nonexistent_request(db_session):
    """Test la récupération d'une requête PDF inexistante."""
    service = PDFService(db_session)
    request = await service.get_request(999)
    assert request is None

@pytest.mark.asyncio
async def test_delete_request(db_session):
    """Test la suppression d'une requête PDF."""
    service = PDFService(db_session)
    
    # Créer une requête
    request_data = PDFRequestCreate(
        template_name="test_template",
        data={"key": "value"}
    )
    created_request = await service.create_request(request_data, user_id=1)
    
    # Supprimer la requête
    result = await service.delete_request(created_request.id)
    assert result is True
    
    # Vérifier que la requête a été supprimée
    deleted_request = await service.get_request(created_request.id)
    assert deleted_request is None

@pytest.mark.asyncio
async def test_delete_nonexistent_request(db_session):
    """Test la suppression d'une requête PDF inexistante."""
    service = PDFService(db_session)
    result = await service.delete_request(999)
    assert result is False

@pytest.mark.asyncio
async def test_process_request_success(db_session, mocker):
    """Test le traitement réussi d'une requête PDF."""
    service = PDFService(db_session)
    
    # Mock du template_manager
    mock_generate_pdf = mocker.patch.object(
        service.template_manager,
        'generate_pdf',
        return_value="/path/to/generated.pdf"
    )
    
    # Créer une requête
    request_data = PDFRequestCreate(
        template_name="test_template",
        data={"key": "value"}
    )
    created_request = await service.create_request(request_data, user_id=1)
    
    # Traiter la requête
    processed_request = await service.process_request(created_request.id)
    assert processed_request.status == "completed"
    assert processed_request.file_path == "/path/to/generated.pdf"
    assert processed_request.processing_time is not None
    assert processed_request.error is None
    
    # Vérifier que generate_pdf a été appelé
    mock_generate_pdf.assert_called_once_with(
        "test_template",
        {"key": "value"},
        None
    )

@pytest.mark.asyncio
async def test_process_request_template_not_found(db_session, mocker):
    """Test le traitement d'une requête PDF avec un template inexistant."""
    service = PDFService(db_session)
    
    # Mock du template_manager pour lever une exception
    mocker.patch.object(
        service.template_manager,
        'generate_pdf',
        side_effect=TemplateNotFoundException("test_template", "/templates")
    )
    
    # Créer une requête
    request_data = PDFRequestCreate(
        template_name="test_template",
        data={"key": "value"}
    )
    created_request = await service.create_request(request_data, user_id=1)
    
    # Traiter la requête
    processed_request = await service.process_request(created_request.id)
    assert processed_request.status == "failed"
    assert processed_request.error is not None
    assert "Template PDF 'test_template' non trouvé" in processed_request.error
    assert processed_request.processing_time is not None 