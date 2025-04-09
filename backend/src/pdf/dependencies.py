"""
Dépendances pour le module PDF.
"""
from typing import Annotated
# Removed: Generator, Optional
from fastapi import Depends
# Removed: HTTPException, status
# Removed: sqlalchemy.orm Session
# Import AsyncSession and the dependency function
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db_session

# Configuration
from src.pdf.config import PDFSettings, pdf_settings

# Domain
from .generator import AbstractPDFGenerator # Use relative import

# Infrastructure
from .reportlab_generator import ReportLabPDFGenerator # Use relative import

# Application
from .services import PDFService # Use relative import

# Database (Keep for now if get_request_by_id is potentially needed elsewhere)
# from src.database import get_db
# from src.pdf.models import PDFRequest # Model used by get_request_by_id

# --- PDF Settings Dependency --- 

def get_pdf_settings() -> PDFSettings:
    """Retourne l'instance globale des paramètres PDF."""
    return pdf_settings

PDFSettingsDep = Annotated[PDFSettings, Depends(get_pdf_settings)]

# --- PDF Generator Dependency --- 

def get_pdf_generator(
    settings: PDFSettingsDep
) -> AbstractPDFGenerator:
    """Fournit une instance de l'implémentation concrète du PDF Generator,
    en injectant la configuration.
    """
    return ReportLabPDFGenerator(settings=settings)

PDFGeneratorDep = Annotated[AbstractPDFGenerator, Depends(get_pdf_generator)]

# --- PDF Service Dependency (Updated) --- 

def get_pdf_service(
    pdf_generator: PDFGeneratorDep,
    db: AsyncSession = Depends(get_db_session) # Inject AsyncSession
) -> PDFService:
    """Injecte le PDF Generator et la session DB, puis fournit une instance de PDFService."""
    # Pass both dependencies to the service constructor
    return PDFService(pdf_generator=pdf_generator, db=db)

PDFServiceDep = Annotated[PDFService, Depends(get_pdf_service)]

# --- Old Dependencies (Commented out - Review if needed) ---

# def get_pdf_service(db: Session = Depends(get_db)) -> PDFService:
#     """OLD VERSION: Fournit une instance du service PDF (requiert DB)."""
#     # This version seems outdated as PDFService now depends on AbstractPDFGenerator
#     # return PDFService(db) # Original line
#     raise NotImplementedError("This dependency seems outdated. Use the generator-based one.")

# def get_request_by_id(
#     request_id: int,
#     db: Session = Depends(get_db)
# ) -> Generator[PDFRequest, None, None]:
#     """
#     Récupère une requête PDF par son ID.
#     This function interacts directly with the DB.
#     Consider if this logic belongs in a repository or another service.
#     """
#     request = db.query(PDFRequest).filter(PDFRequest.id == request_id).first()
#     if not request:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"PDF request with id {request_id} not found"
#         )
#     yield request 