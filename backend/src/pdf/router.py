"""
Routes FastAPI pour le module PDF.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

# Import dependencies
from src.pdf.dependencies import PDFServiceDep
# Import schemas
from src.pdf.models import PDFRequestCreate, PDFRequestRead
# Import service
from src.pdf.service import PDFService
# Import exceptions
from src.pdf.exceptions import PDFGenerationException

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/pdfs", # Base path for all routes in this router
    tags=["PDF Management"], # Tag for OpenAPI documentation
    responses={404: {"description": "Not found"}}, # Default 404 response
)

@router.post("/requests/", response_model=PDFRequestRead, status_code=status.HTTP_202_ACCEPTED)
async def create_pdf_request(
    request_data: PDFRequestCreate,
    background_tasks: BackgroundTasks,
    pdf_service: PDFServiceDep, # Inject the PDF service
    # TODO: Add dependency for getting current user ID
    # current_user_id: int = Depends(get_current_user_id) 
):
    """
    Accepte une nouvelle demande de génération de PDF et lance le traitement en arrière-plan.

    Args:
        request_data: Données pour la création de la requête (template, data, options).
        background_tasks: Tâches d'arrière-plan FastAPI.
        pdf_service: Service PDF injecté.
        # current_user_id: ID de l'utilisateur courant (à implémenter).

    Returns:
        PDFRequestRead: Les détails de la requête PDF créée (statut initial "pending").
    """
    logger.info(f"Reçu une demande de création de PDF: {request_data.template_name}")
    try:
        # For now, let's use a placeholder user ID
        user_id_placeholder = 1 
        
        # Create the request record in the database first
        created_request = await pdf_service.create_request(
            request_data=request_data,
            user_id=user_id_placeholder # Replace with actual user ID
        )
        
        # Add the PDF generation task to the background
        background_tasks.add_task(pdf_service.process_request, created_request.id)
        logger.info(f"Tâche de génération PDF #{created_request.id} ajoutée en arrière-plan.")
        
        # Return the created request details immediately
        return created_request
        
    except Exception as e:
        logger.error(f"Erreur lors de la création de la requête PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne lors de la création de la requête PDF: {e}"
        )

@router.get("/requests/{request_id}", response_model=PDFRequestRead)
async def get_pdf_request_status(
    request_id: int,
    pdf_service: PDFServiceDep, # Inject the PDF service
):
    """
    Récupère le statut et les détails d'une requête de génération PDF par son ID.

    Args:
        request_id: ID de la requête PDF.
        pdf_service: Service PDF injecté.

    Returns:
        PDFRequestRead: Détails de la requête PDF.
        
    Raises:
        HTTPException (404): Si la requête n'est pas trouvée.
    """
    logger.debug(f"Recherche de la requête PDF #{request_id}.")
    request = await pdf_service.get_request(request_id)
    if not request:
        logger.warning(f"Requête PDF #{request_id} non trouvée.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF request with id {request_id} not found"
        )
    logger.debug(f"Requête PDF #{request_id} trouvée (Statut: {request.status}).")
    return request

# TODO: Add more endpoints as needed:
# - List requests (with pagination/filtering)
# - Delete a request
# - Download the generated PDF (requires handling file responses) 