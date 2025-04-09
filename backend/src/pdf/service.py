"""
Service pour la génération et la gestion des PDFs (requêtes).
"""
import os
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Use AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Import the SQLModel schemas
from src.pdf.models import PDFRequest, PDFRequestCreate, PDFRequestRead, PDFRequestUpdate
# Import the generator interface
from src.pdf.generator import AbstractPDFGenerator
# Import custom exceptions
from src.pdf.exceptions import PDFGenerationException, TemplateNotFoundException

logger = logging.getLogger(__name__)

class PDFService:
    """
    Service pour la gestion des requêtes de génération de PDF.
    Combine la logique de persistance (via DB) et de génération (via generator).
    """
    def __init__(self, db: AsyncSession, pdf_generator: AbstractPDFGenerator):
        """
        Initialise le service PDF.
        
        Args:
            db: Session de base de données asynchrone
            pdf_generator: Instance d'un générateur de PDF concret.
        """
        self.db = db
        self.pdf_generator = pdf_generator
        # Removed: self.template_manager = PDFTemplateManager()
        
    async def create_request(
        self,
        request_data: PDFRequestCreate, # Use the Create schema
        user_id: int
    ) -> PDFRequestRead: # Return the Read schema
        """
        Crée une nouvelle requête PDF dans la base de données.
        
        Args:
            request_data: Données pour la création de la requête (schéma Create)
            user_id: ID de l'utilisateur
            
        Returns:
            PDFRequestRead: La requête créée (schéma Read)
        """
        # Create the DB model instance
        db_request = PDFRequest(
            **request_data.model_dump(), # Use model_dump() for SQLModel >= v0.0.7
            user_id=user_id,
            created_at=datetime.utcnow(),
            status="pending" # Initial status
        )
        self.db.add(db_request)
        try:
            await self.db.commit()
            await self.db.refresh(db_request)
            logger.info(f"Nouvelle requête PDF #{db_request.id} créée pour l'utilisateur {user_id}.")
            # Return data using the Read schema
            return PDFRequestRead.model_validate(db_request) # Use model_validate for Pydantic v2
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Erreur lors de la création de la requête PDF pour user {user_id}: {e}", exc_info=True)
            # Re-raise or handle appropriately
            raise
        
    async def process_request(self, request_id: int) -> PDFRequestRead: # Return the Read schema
        """
        Traite une requête PDF: génère le PDF et met à jour le statut.
        
        Args:
            request_id: ID de la requête
            
        Returns:
            PDFRequestRead: La requête mise à jour (schéma Read)
            
        Raises:
            ValueError: Si la requête n'est pas trouvée.
            PDFGenerationException: Si la génération échoue.
        """
        # Fetch the request from DB
        request = await self.get_request_internal(request_id) # Use internal helper
        if not request:
            logger.warning(f"Tentative de traitement de la requête PDF inexistante #{request_id}.")
            raise ValueError(f"Request {request_id} not found")
            
        logger.info(f"Traitement de la requête PDF #{request_id} (template: {request.template_name}).")
        start_time = time.time()
        request.status = "processing" # Mark as processing
        try:
            # Generate PDF using the injected generator
            # Note: The AbstractPDFGenerator interface might need adjustment
            # if it doesn't have a generic 'generate_pdf' method.
            # Assuming a generic method exists or adapting here:
            # For now, let's assume the generator handles template/data/options
            
            # --- Placeholder for actual generation logic --- 
            # This needs to match the AbstractPDFGenerator interface.
            # If the generator has specific methods (like generate_quote_pdf), 
            # this logic needs to adapt based on request.template_name or data.
            # Example using a hypothetical generic method:
            pdf_content_or_path = await self.pdf_generator.generate_pdf(
                 template_name=request.template_name,
                 data=request.data,
                 options=request.options
             )
            # --- End Placeholder --- 
            
            # Assuming generate_pdf returns the file path:
            file_path = pdf_content_or_path 
            
            # Update request status
            request.status = "completed"
            request.file_path = file_path
            request.processing_time = time.time() - start_time
            request.error = None
            logger.info(f"Requête PDF #{request_id} traitée avec succès. Fichier: {file_path}")
            
        except (PDFGenerationException, TemplateNotFoundException) as e:
            request.status = "failed"
            request.error = str(e)
            request.processing_time = time.time() - start_time
            logger.error(f"Échec du traitement de la requête PDF #{request_id}: {e}")
        except Exception as e:
            request.status = "failed"
            request.error = f"Erreur inattendue: {str(e)}"
            request.processing_time = time.time() - start_time
            logger.error(f"Erreur inattendue lors du traitement de la requête PDF #{request_id}: {e}", exc_info=True)
            
        # Commit changes (status, file_path, error, time)
        try:
            await self.db.commit()
            await self.db.refresh(request)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Erreur lors de la sauvegarde du statut de la requête PDF #{request_id}: {e}", exc_info=True)
            # Depending on requirements, might re-raise or just log
            raise PDFGenerationException(f"Failed to save request status after processing: {e}")
            
        return PDFRequestRead.model_validate(request)
        
    async def get_request_internal(self, request_id: int) -> Optional[PDFRequest]:
        """Helper interne pour récupérer un objet PDFRequest DB."""
        result = await self.db.execute(select(PDFRequest).where(PDFRequest.id == request_id))
        return result.scalar_one_or_none()

    async def get_request(self, request_id: int) -> Optional[PDFRequestRead]:
        """
        Récupère une requête PDF par son ID et la retourne au format Read.
        
        Args:
            request_id: ID de la requête
            
        Returns:
            Optional[PDFRequestRead]: La requête trouvée (schéma Read) ou None
        """
        request = await self.get_request_internal(request_id)
        if request:
            return PDFRequestRead.model_validate(request)
        return None
        
    async def delete_request(self, request_id: int) -> bool:
        """
        Supprime une requête PDF et son fichier associé (si existant).
        
        Args:
            request_id: ID de la requête à supprimer
            
        Returns:
            bool: True si la suppression a réussi, False si non trouvée.
        """
        request = await self.get_request_internal(request_id)
        if not request:
            logger.warning(f"Tentative de suppression de la requête PDF inexistante #{request_id}.")
            return False
            
        # Delete the associated PDF file if it exists
        file_path_to_delete = request.file_path
        if file_path_to_delete and os.path.exists(file_path_to_delete):
            try:
                os.remove(file_path_to_delete)
                logger.info(f"Fichier PDF associé {file_path_to_delete} supprimé pour la requête #{request_id}.")
            except OSError as e:
                logger.error(f"Impossible de supprimer le fichier PDF {file_path_to_delete} pour la requête #{request_id}: {e}")
                # Decide if deletion should fail or continue
        
        # Delete the DB record
        try:
            await self.db.delete(request)
            await self.db.commit()
            logger.info(f"Requête PDF #{request_id} supprimée de la base de données.")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Erreur lors de la suppression de la requête PDF #{request_id} de la DB: {e}", exc_info=True)
            # Re-raise or handle appropriately
            raise 