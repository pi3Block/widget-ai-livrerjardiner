"""
Gestionnaire de templates PDF.
"""
import os
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from pathlib import Path
import logging

class PDFTemplateManager:
    """
    Gestionnaire de templates PDF utilisant WeasyPrint et Jinja2.
    """
    
    def __init__(self, templates_dir: str = "src/pdf/templates"):
        """
        Initialise le gestionnaire de templates.
        
        Args:
            templates_dir: Chemin vers le répertoire contenant les templates
        """
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True
        )
        self.logger = logging.getLogger(__name__)
        
    def render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """
        Rendu d'un template avec les données fournies.
        
        Args:
            template_name (str): Nom du template à utiliser
            data (Dict[str, Any]): Données à injecter dans le template
            
        Returns:
            str: HTML généré
        """
        template = self.env.get_template(template_name)
        return template.render(**data)
    
    def generate_pdf(
        self,
        template_name: str,
        data: Dict[str, Any],
        output_dir: Path,
        filename: str,
        css_file: Optional[str] = None
    ) -> Path:
        """
        Génère un PDF à partir d'un template HTML et des données fournies.
        
        Args:
            template_name: Nom du fichier template HTML
            data: Données à injecter dans le template
            output_dir: Répertoire de sortie pour le PDF
            filename: Nom du fichier PDF à générer
            css_file: Fichier CSS optionnel pour le style
            
        Returns:
            Path: Chemin vers le fichier PDF généré
        """
        try:
            # Créer le répertoire de sortie si nécessaire
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / filename
            
            # Charger et rendre le template
            template = self.env.get_template(template_name)
            html_content = template.render(**data)
            
            # Préparer les styles CSS
            css = None
            if css_file:
                css_path = self.templates_dir / css_file
                if css_path.exists():
                    css = CSS(filename=str(css_path))
            
            # Générer le PDF
            HTML(string=html_content).write_pdf(
                str(output_path),
                stylesheets=[css] if css else None
            )
            
            self.logger.info(f"PDF généré avec succès: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération du PDF: {str(e)}")
            raise
        
    def get_available_templates(self) -> list[str]:
        """
        Récupère la liste des templates disponibles.
        
        Returns:
            list[str]: Liste des noms de templates
        """
        return [
            f.stem for f in self.templates_dir.glob("*.html")
        ] 