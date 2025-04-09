"""Configuration spécifique au module PDF.

Utilise Pydantic BaseSettings pour permettre la surcharge par
des variables d'environnement si nécessaire.
"""

from pydantic_settings import BaseSettings
from reportlab.lib import colors # Nécessaire pour définir la couleur

class PDFSettings(BaseSettings):
    """Paramètres de configuration pour la génération de PDF."""

    LOGO_PATH: str = "backend/static/logo.png"
    TMP_PDF_DIR: str = "temp_pdfs" # Dossier pour sauvegarde temporaire
    COMPANY_INFO_HTML: str = (
        "<b>LivrerJardiner.fr</b><br/>"
        "123 Rue des Jardins, 75000 Paris<br/>"
        "Email : contact@livrerjardiner.fr<br/>"
        "Tél : +33 1 23 45 67 89"
    )
    FOOTER_TEXT: str = "LivrerJardiner.fr - Votre partenaire pour un jardin fleuri"
    PRIMARY_COLOR_HEX: str = "#5a9a1f" # Stocker la couleur comme string HEX

    # Permet de charger depuis un fichier .env si présent
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

# Instance globale unique des paramètres (peut être utilisée directement ou injectée)
pdf_settings = PDFSettings() 