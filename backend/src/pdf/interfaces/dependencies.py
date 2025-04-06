from typing import Annotated
from fastapi import Depends

# Domain
from src.pdf.domain.generator import AbstractPDFGenerator

# Infrastructure
from src.pdf.infrastructure.reportlab_generator import ReportLabPDFGenerator

# Application
from src.pdf.application.services import PDFService

# --- PDF Generator Dependency ---

def get_pdf_generator() -> AbstractPDFGenerator:
    """Fournit une instance de l'implémentation concrète du PDF Generator.
    
    Actuellement, utilise ReportLabPDFGenerator.
    """
    return ReportLabPDFGenerator()

PDFGeneratorDep = Annotated[AbstractPDFGenerator, Depends(get_pdf_generator)]

# --- PDF Service Dependency ---

def get_pdf_service(
    pdf_generator: PDFGeneratorDep
) -> PDFService:
    """Injecte le PDF Generator et fournit une instance de PDFService."""
    return PDFService(pdf_generator=pdf_generator)

PDFServiceDep = Annotated[PDFService, Depends(get_pdf_service)] 