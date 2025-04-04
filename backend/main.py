import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import psycopg2
from psycopg2 import OperationalError, ProgrammingError
import random
import re
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
import os
from dotenv import load_dotenv
from typing import Optional
from pydantic import BaseModel, EmailStr
import time
from fastapi.concurrency import run_in_threadpool
from datetime import datetime
import json

# Configurer le logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configurer CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://livrerjardiner.fr",
        "https://cdn.jsdelivr.net",
        "https://pierrelegrand.fr",
        "http://localhost:3000",
        "https://pi3block.github.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Liste de messages d'erreur amusants
ERROR_MESSAGES = [
    "Oups, on dirait que nos rosiers ont pris des vacances ! Réessaie dans un instant.",
    "Aïe, le jardinier a trébuché sur un câble... On répare ça vite !",
    "Le stock a décidé de jouer à cache-cache. Patience, on le retrouve !",
    "Erreur 404 : Rosiers introuvables... ou peut-être qu'ils se sont enfuis ?",
    "Notre base de données fait la sieste. On la réveille avec un café !",
]

# Charger les variables d'environnement
load_dotenv()
sender_email = os.getenv("SENDER_EMAIL", "robotia@livrerjardiner.fr")
sender_password = os.getenv("SENDER_PASSWORD", "tonmotdepasse")
smtp_host = os.getenv("SMTP_HOST", "smtp.hostinger.com")
smtp_port = int(os.getenv("SMTP_PORT", "465"))
postgres_password = os.getenv("POSTGRES_PASSWORD", "motPAsse")

logger.info(f"SENDER_EMAIL={sender_email}, SMTP_HOST={smtp_host}, SMTP_PORT={smtp_port}")

# Classe SMTPHostinger pour envoyer des emails via Hostinger
class SMTPHostinger:
    """
    SMTP module for Hostinger emails
    """
    def __init__(self):
        self.conn = None

    def auth(self, user: str, password: str, host: str, port: int, debug: bool = False):
        """
        Authenticates a session
        """
        self.user = user
        self.password = password
        self.host = host
        self.port = port

        context = ssl.create_default_context()

        self.conn = smtplib.SMTP_SSL(host, port, context=context)
        self.conn.set_debuglevel(debug)

        try:
            self.conn.login(user, password)
            logger.debug("Connexion SMTP réussie")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Erreur d'authentification SMTP : {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la connexion SMTP : {str(e)}")
            return False

    def send(self, recipient: str, sender: str, subject: str, message: str):
        """
        Sends an email to the specified recipient.
        Assumes 'message' is a fully formatted email string (e.g., from msg.as_string()).
        The subject parameter is ignored here as it should be part of the message string.
        """
        if self.conn:
            try:
                # Envoyer directement la chaîne 'message' formatée
                # Assurer que le destinataire est une liste
                self.conn.sendmail(sender, [recipient], message)
                logger.debug(f"Email envoyé à {recipient}")
                return True
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'email : {str(e)}")
                return False
        else:
            logger.error("Connexion SMTP non établie")
            return False

    def close(self):
        """
        Closes the SMTP connection
        """
        if self.conn:
            try:
                self.conn.quit()
                logger.debug("Connexion SMTP fermée proprement via quit()")
            except smtplib.SMTPServerDisconnected:
                logger.warning("Tentative de fermeture (quit) sur une connexion SMTP déjà déconnectée.")
            except Exception as e:
                logger.error(f"Erreur inattendue lors de la fermeture SMTP (quit) : {str(e)}")
            finally:
                self.conn = None # Assurer que self.conn est None après tentative de fermeture
        else:
             logger.debug("Aucune connexion SMTP active à fermer.")

DB_CONNECT_ERROR_MSG = "Connexion à la base de données impossible pour le moment. Veuillez réessayer."
DB_SQL_ERROR_MSG = "Un problème technique est survenu avec la base de données."

def check_stock(item: str) -> int:
    logger.debug(f"Vérification du stock pour l'article : {item}")
    conn = None # Initialiser à None
    try:
        conn = psycopg2.connect(dbname="livrerjardiner", user="monuser", password="moncode") # Mettre les vrais identifiants ou via env var
        cur = conn.cursor()
        cur.execute("SELECT quantity FROM stock WHERE item=%s", (item,))
        result = cur.fetchone()
        stock = result[0] if result else 0
        logger.debug(f"Stock trouvé : {stock}")
        return stock
    except OperationalError as e:
        logger.error(f"Erreur opérationnelle DB dans check_stock : {str(e)}")
        raise HTTPException(status_code=503, detail=DB_CONNECT_ERROR_MSG)
    except ProgrammingError as e:
        logger.error(f"Erreur SQL dans check_stock : {str(e)}")
        raise HTTPException(status_code=500, detail=DB_SQL_ERROR_MSG)
    except Exception as e:
        logger.error(f"Erreur inattendue dans check_stock : {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la vérification du stock.")
    finally:
        if conn:
            conn.close()
            logger.debug("Connexion DB fermée dans check_stock")

def generate_quote_pdf(item: str, quantity: int, unit_price: float, total_price: float, quote_id: int) -> str:
    logger.debug(f"Génération du PDF pour le devis #{quote_id}")
    pdf_path = f"quotes/quote_{quote_id}.pdf"

    try:
        os.makedirs("quotes", exist_ok=True)
        logger.debug(f"Dossier quotes créé ou existant")

        # Créer un document PDF
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        elements = []

        # Styles pour le texte
        styles = getSampleStyleSheet()
        title_style = styles["Heading1"]
        # title_style.textColor = colors.darkgreen # Utiliser une couleur standard ou définir la vôtre
        title_style.textColor = colors.HexColor("#5a9a1f") # Utiliser le vert LivrerJardiner
        normal_style = styles["Normal"]
        normal_style.textColor = colors.black
        footer_style = ParagraphStyle(
            name="Footer",
            fontSize=10,
            textColor=colors.gray,
            alignment=1  # Centré (TA_CENTER)
        )

        # En-tête : Logo ou titre stylisé
        logo_path = "static/logo.png"  # Assurez-vous que ce chemin est correct
        try:
             if os.path.exists(logo_path):
                logo = Image(logo_path, width=1.5*inch, height=0.75*inch) # Ajuster taille au besoin
                logo.hAlign = 'LEFT' # Aligner à gauche
                elements.append(logo)
             else:
                logger.warning(f"Logo non trouvé à l'emplacement : {logo_path}")
                # Si pas de logo, utiliser un titre stylisé
                title = Paragraph("LivrerJardiner.fr", title_style)
                elements.append(title)
        except Exception as img_err:
            logger.error(f"Erreur lors du chargement du logo: {img_err}. Utilisation du titre.")
            title = Paragraph("LivrerJardiner.fr", title_style)
            elements.append(title)

        elements.append(Spacer(1, 0.1*inch)) # Espace après logo/titre

        # Informations de l'entreprise (à droite)
        # Utiliser un style séparé pour aligner à droite si nécessaire ou mettre dans un tableau
        company_info_text = (
            "<b>LivrerJardiner.fr</b><br/>"
            "123 Rue des Jardins, 75000 Paris<br/>"
            "Email : contact@livrerjardiner.fr<br/>"
            "Tél : +33 1 23 45 67 89"
        )
        company_info_style = ParagraphStyle(name='CompanyInfo', parent=normal_style, alignment=2) # 2=TA_RIGHT
        company_info = Paragraph(company_info_text, company_info_style)
        # Pour positionner, on peut utiliser un tableau ou des frames plus tard
        elements.append(company_info)
        elements.append(Spacer(1, 0.2*inch))

        # Titre du devis
        quote_title = Paragraph(f"Devis #{quote_id}", styles["h2"]) # Utiliser h2
        elements.append(quote_title)

        # Date
        date_str = datetime.now().strftime('%d/%m/%Y')
        date_paragraph = Paragraph(f"Date : {date_str}", normal_style)
        elements.append(date_paragraph)
        elements.append(Spacer(1, 0.3*inch))

        # Tableau des articles
        data = [
            ["Article", "Quantité", "Prix unitaire (€)", "Total (€)"],
            # Utiliser Paragraph pour permettre le retour à la ligne si item est long
            [Paragraph(item, normal_style), str(quantity), f"{unit_price:.2f}", f"{total_price:.2f}"]
        ]
        table = Table(data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch]) # Ajuster largeurs
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5a9a1f")), # Vert
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), # Centrer verticalement
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F0F0F0")), # Fond gris clair
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 1, colors.darkgrey), # Grille plus discrète
            ("TOPPADDING", (0, 1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.5*inch))

        # Message de validation
        validation_message = Paragraph(
            "Merci de valider ce devis pour confirmer votre commande.<br/>"
            "Pour toute question, contactez-nous à contact@livrerjardiner.fr.",
            normal_style
        )
        elements.append(validation_message)

        # Pied de page (sera ajouté par la fonction onPage)
        def add_footer(canvas, doc):
            canvas.saveState()
            footer = Paragraph("LivrerJardiner.fr - Votre partenaire pour un jardin fleuri", footer_style)
            w, h = footer.wrap(doc.width, doc.bottomMargin)
            footer.drawOn(canvas, doc.leftMargin, h) # Position en bas
            canvas.restoreState()

        # Générer le PDF avec pied de page
        doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
        logger.debug(f"PDF généré avec succès : {pdf_path}")
        return pdf_path
    except Exception as e:
        logger.error(f"Erreur lors de la génération du PDF : {str(e)}", exc_info=True)
        raise # Propager l'erreur pour que l'appelant la gère

def save_quote(user_email: str, item: str, quantity: int) -> int:
    logger.debug(f"Sauvegarde du devis pour {user_email}, item={item}, quantity={quantity}")
    unit_price = 5.0
    total_price = unit_price * quantity
    conn = None
    try:
        conn = psycopg2.connect(dbname="livrerjardiner", user="monuser", password="moncode")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO quotes (user_email, item, quantity, unit_price, total_price) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (user_email, item, quantity, unit_price, total_price)
        )
        quote_id = cur.fetchone()[0]
        # La génération PDF peut aussi lever une erreur, gérée en dehors
        pdf_path = generate_quote_pdf(item, quantity, unit_price, total_price, quote_id)
        cur.execute("UPDATE quotes SET pdf_path=%s WHERE id=%s", (pdf_path, quote_id))
        conn.commit()
        logger.debug(f"Devis sauvegardé : quote_id={quote_id}")
        return quote_id
    except OperationalError as e:
        logger.error(f"Erreur opérationnelle DB dans save_quote : {str(e)}")
        raise HTTPException(status_code=503, detail=DB_CONNECT_ERROR_MSG)
    except ProgrammingError as e:
        logger.error(f"Erreur SQL dans save_quote : {str(e)}")
        # Peut-être annuler la transaction si possible ?
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=DB_SQL_ERROR_MSG)
    except Exception as e:
        logger.error(f"Erreur inattendue dans save_quote : {str(e)}", exc_info=True)
        if conn: conn.rollback()
        # Propager ou lever une HTTP 500 plus spécifique à l'échec de sauvegarde
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du devis: {e}")
    finally:
        if conn:
            conn.close()
            logger.debug("Connexion DB fermée dans save_quote")

def save_pending_order(user_email: str, item: str, quantity: int):
    logger.debug(f"Sauvegarde d'une commande en attente pour {user_email}...")
    conn = None
    try:
        conn = psycopg2.connect(dbname="livrerjardiner", user="monuser", password="moncode")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO pending_orders (user_email, item, quantity) VALUES (%s, %s, %s)",
            (user_email, item, quantity)
        )
        conn.commit()
        logger.debug("Commande en attente sauvegardée")
    except OperationalError as e:
        logger.error(f"Erreur opérationnelle DB dans save_pending_order : {str(e)}")
        raise HTTPException(status_code=503, detail=DB_CONNECT_ERROR_MSG)
    except ProgrammingError as e:
        logger.error(f"Erreur SQL dans save_pending_order : {str(e)}")
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=DB_SQL_ERROR_MSG)
    except Exception as e:
        logger.error(f"Erreur inattendue dans save_pending_order : {str(e)}", exc_info=True)
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde de la commande en attente.")
    finally:
        if conn:
            conn.close()
            logger.debug("Connexion DB fermée dans save_pending_order")

def save_order(user_email: str, item: str, quantity: int, delivery_method: str):
    logger.debug(f"Sauvegarde de la commande pour {user_email}...")
    conn = None
    try:
        conn = psycopg2.connect(dbname="livrerjardiner", user="monuser", password="moncode")
        cur = conn.cursor()
        # Potentiellement utiliser une transaction ici
        cur.execute(
            "INSERT INTO orders (user_email, item, quantity, delivery_method) VALUES (%s, %s, %s, %s)",
            (user_email, item, quantity, delivery_method)
        )
        cur.execute("UPDATE stock SET quantity = quantity - %s WHERE item=%s", (quantity, item))
        # Vérifier si la mise à jour du stock a réussi (ex: stock non négatif)
        # ... logique de vérification supplémentaire ici ...
        conn.commit()
        logger.debug("Commande sauvegardée et stock mis à jour")
    except OperationalError as e:
        logger.error(f"Erreur opérationnelle DB dans save_order : {str(e)}")
        raise HTTPException(status_code=503, detail=DB_CONNECT_ERROR_MSG)
    except ProgrammingError as e:
        logger.error(f"Erreur SQL dans save_order : {str(e)}")
        if conn: conn.rollback() # Important dans une transaction
        raise HTTPException(status_code=500, detail=DB_SQL_ERROR_MSG)
    except Exception as e:
        logger.error(f"Erreur inattendue dans save_order : {str(e)}", exc_info=True)
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la finalisation de la commande.")
    finally:
        if conn:
            conn.close()
            logger.debug("Connexion DB fermée dans save_order")

def send_quote_email(user_email: str, quote_id: int, pdf_path: str):
    logger.debug(f"Préparation de l'email à {user_email} pour le devis #{quote_id}")
    subject = f"Devis #{quote_id} - LivrerJardiner.fr"
    body = f"""
    Bonjour,

    Voici votre devis #{quote_id} pour votre commande. Veuillez le valider pour confirmer.

    Merci de votre confiance,
    L'équipe LivrerJardiner.fr
    """

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = user_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with open(pdf_path, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
            attach.add_header("Content-Disposition", "attachment", filename=f"devis_{quote_id}.pdf")
            msg.attach(attach)
    except Exception as e:
        logger.error(f"Erreur lors de la lecture ou attachement du PDF pour l'email : {str(e)}")
        return False # Ne pas tenter d'envoyer si le PDF échoue

    # Créer, authentifier, envoyer et fermer la connexion pour cet email spécifique
    local_smtp_client = SMTPHostinger()
    email_sent = False
    try:
        logger.debug(f"Tentative d'authentification SMTP pour l'envoi à {user_email}")
        if local_smtp_client.auth(sender_email, sender_password, smtp_host, smtp_port, debug=True):
            logger.debug(f"Authentification réussie. Tentative d'envoi à {user_email}")
            email_sent = local_smtp_client.send(
                recipient=user_email,
                sender=sender_email,
                subject=subject, # Ignoré par send mais passé pour cohérence
                message=msg.as_string()
            )
            if not email_sent:
                logger.error(f"La méthode send a retourné False pour {user_email}")
        else:
            logger.error(f"Échec de l'authentification SMTP lors de la tentative d'envoi à {user_email}")

    except Exception as e:
        logger.error(f"Exception lors de l'envoi de l'email à {user_email}: {str(e)}", exc_info=True)
        email_sent = False
    finally:
        logger.debug(f"Fermeture de la connexion SMTP pour l'envoi à {user_email}")
        local_smtp_client.close()

    if not email_sent:
        logger.error(f"Échec final de l'envoi de l'email de devis à {user_email}")
    return email_sent

try:
    llm = OllamaLLM(model="mistral", base_url="http://localhost:11434")
    logger.info("LLM initialisé avec succès")
except Exception as e:
    logger.error(f"Erreur lors de l'initialisation du LLM : {str(e)}")
    llm = None

# Prompt principal pour les requêtes liées au stock
stock_prompt = PromptTemplate(
    input_variables=["input", "stock", "quantity", "item", "is_enough"],
    template="L'utilisateur demande : {input}. Le stock actuel est de {stock} {item} pour une demande de {quantity}. Le stock est-il suffisant ? {is_enough}. Réponds de manière utile et conviviale, en français uniquement."
)

# Prompt simple pour la conversation générale
general_chat_prompt = PromptTemplate(
    input_variables=["input"],
    template="L'utilisateur demande : {input}. Réponds de manière utile, conviviale et pertinente, en français uniquement."
)

# NOUVEAU: Prompt pour le parsing initial (Intent + Entities)
parsing_prompt_template = """Analyse la demande de l'utilisateur suivante et retourne un objet JSON valide avec les clés "intent" et "entities".
Les intents possibles sont: "verifier_stock", "demande_quantite", "info_generale".
Les entités possibles dans l'objet "entities" sont: "item" (le nom normalisé de l'article, en minuscule et singulier si possible) et "quantity" (le nombre entier demandé).
Si une entité n'est pas trouvée ou non applicable, retourne null pour sa valeur ou omet la clé. Ne retourne que le JSON, sans texte explicatif avant ou après.

Demande Utilisateur: "{input}"

JSON:
"""
parsing_prompt = PromptTemplate(input_variables=["input"], template=parsing_prompt_template)

@app.get("/chat")
async def chat(input: str, delivery_method: str = "livraison", user_email: Optional[str] = None):
    logger.info(f"Requête chat reçue : input={input}, user_email={user_email}, delivery_method={delivery_method}")
    if not llm:
        logger.error("LLM non disponible")
        return {"message": "Désolé, notre assistant IA est en grève pour plus de soleil ! Réessaie plus tard.", "can_order": False, "item": None, "quantity": None} # Retourner None pour item/qty

    # --- Étape 1 : Parsing de l'intention et des entités via LLM ---
    parsed_intent = "info_generale" # Défaut
    extracted_item = None
    extracted_quantity = None
    parsing_error = None

    try:
        logger.debug("Appel LLM pour parsing intent/entities...")
        parsing_formatted_prompt = parsing_prompt.format(input=input)
        # Utiliser run_in_threadpool pour l'appel LLM
        parsing_response_raw = await run_in_threadpool(llm.invoke, parsing_formatted_prompt)
        logger.debug(f"Réponse brute du parsing LLM: {parsing_response_raw}")

        # Nettoyer et parser la réponse JSON
        json_str = parsing_response_raw.strip().strip('```json').strip('```').strip()
        parsed_data = json.loads(json_str)

        parsed_intent = parsed_data.get("intent", "info_generale")
        entities = parsed_data.get("entities", {})
        extracted_item = entities.get("item")
        extracted_quantity = entities.get("quantity")

        # Validation basique
        if extracted_item is not None and not isinstance(extracted_item, str):
             logger.warning(f"Item extrait non valide (type {type(extracted_item)}): {extracted_item}. Ignoré.")
             extracted_item = None
        if extracted_quantity is not None:
            try:
                # Gérer le cas où la quantité est None ou une chaîne vide avant int()
                if extracted_quantity == '' or extracted_quantity is None:
                    extracted_quantity = None
                else:
                    extracted_quantity = int(extracted_quantity)
            except (ValueError, TypeError):
                 logger.warning(f"Quantité extraite non valide (valeur {extracted_quantity}). Ignorée.")
                 extracted_quantity = None

        logger.info(f"Parsing LLM réussi: intent={parsed_intent}, item={extracted_item}, quantity={extracted_quantity}")

    except json.JSONDecodeError as e:
        parsing_error = f"Erreur de décodage JSON de la réponse du parsing LLM: {e}"
        logger.error(parsing_error)
    except Exception as e:
        parsing_error = f"Erreur inattendue lors du parsing LLM: {e}"
        logger.error(parsing_error, exc_info=True)
        # On continue avec l'intent par défaut "info_generale"

    # --- Fin Étape 1 ---

    # --- Préparation pour la Réponse finale ---
    stock = None
    is_enough = None
    final_prompt_to_use = None
    final_invoke_params = {}
    can_order_flag = False

    # Utiliser les infos parsées pour la structure de retour
    return_data = {
        "message": "",
        "can_order": False,
        "item": extracted_item,
        "quantity": extracted_quantity
    }

    # Si le parsing a échoué, on génère un message d'erreur sans second appel LLM
    if parsing_error:
         return_data["message"] = "Désolé, je n'ai pas bien compris la structure de votre demande. Pouvez-vous reformuler ?"
         logger.debug("Retour anticipé suite à une erreur de parsing LLM.")
         return return_data

    try:
        # --- Étape 2 : Logique basée sur l'intention parsée ---
        is_stock_related_intent = parsed_intent in ["verifier_stock", "demande_quantite"]

        if is_stock_related_intent and extracted_item:
            logger.debug(f"Intent lié au stock détecté pour '{extracted_item}'. Vérification.")
            # TODO: Validation/Normalisation de l'item (ex: via DB)
            item_validated = extracted_item # Utiliser l'item extrait pour l'instant

            stock = await run_in_threadpool(check_stock, item_validated)
            logger.info(f"Stock vérifié pour '{item_validated}': {stock}")

            # Si quantity extraite est None, utiliser 1 pour 'verifier_stock', sinon 0 ?
            # Pour is_enough, si quantity est None, on considère que 1 est demandé implicitement
            current_quantity = extracted_quantity if extracted_quantity is not None and extracted_quantity > 0 else 1
            is_enough = "Oui" if stock >= current_quantity else "Non"
            # Can order flag basé sur is_enough ET si une quantité était réellement demandée ou implicite > 0
            if stock >= current_quantity and current_quantity > 0:
                can_order_flag = True

            final_prompt_to_use = stock_prompt
            final_invoke_params = {
                "input": input,
                "stock": stock,
                "quantity": current_quantity, # Quantité utilisée pour vérifier is_enough
                "item": item_validated,
                "is_enough": is_enough
            }
        else:
            if not extracted_item and is_stock_related_intent:
                 logger.warning(f"Intent {parsed_intent} détecté mais aucun item extrait. Traitement comme info_generale.")
            logger.debug("Traitement comme conversation générale.")
            final_prompt_to_use = general_chat_prompt
            final_invoke_params = {"input": input}

        # --- Étape 3 : Générer la Réponse Finale via LLM ---
        logger.debug(f"Appel LLM pour réponse finale avec prompt: {final_prompt_to_use.template}")
        # Utiliser run_in_threadpool pour le second appel LLM aussi
        final_formatted_prompt = final_prompt_to_use.format(**final_invoke_params)
        final_response = await run_in_threadpool(llm.invoke, final_formatted_prompt)
        logger.info(f"Réponse finale LLM : {final_response}")

        return_data["message"] = final_response
        # Mettre à jour can_order seulement si on a vérifié le stock
        if is_stock_related_intent and extracted_item:
             return_data["can_order"] = can_order_flag

        logger.debug(f"Données de retour finales: {return_data}")
        return return_data

    except HTTPException as e:
        logger.error(f"HTTPException après parsing dans /chat : {str(e)}")
        return_data["message"] = e.detail
        return return_data # Retourner le message d'erreur mais garder le format
    except Exception as e:
        logger.error(f"Erreur inattendue après parsing dans /chat : {str(e)}", exc_info=True)
        error_msg = random.choice(ERROR_MESSAGES)
        return_data["message"] = f"Oups, un problème technique : {error_msg}"
        return return_data

# Modèle Pydantic pour les données de la requête /order
class OrderRequest(BaseModel):
    user_email: EmailStr # Utilise EmailStr pour validation automatique
    item: str
    quantity: int
    delivery_method: str

@app.post("/order")
async def create_order(order_data: OrderRequest):
    """
    Endpoint pour créer un devis, sauvegarder la commande (ou attente) et envoyer l'email.
    Appelé lorsque l'utilisateur clique sur "Commander" et que l'email est validé.
    """
    logger.info(f"Requête /order reçue : {order_data}")

    # Extraire les données validées
    user_email = order_data.user_email
    item = order_data.item
    quantity = order_data.quantity
    delivery_method = order_data.delivery_method

    try:
        # Optionnel : Re-vérifier le stock ici pour être sûr
        stock = await run_in_threadpool(check_stock, item)
        logger.info(f"Stock vérifié pour la commande : stock={stock}")

        # --- LOGIQUE DE COMMANDE/DEVIS/EMAIL DÉPLACÉE ICI ---
        # Étape 1 : Créer un devis
        quote_id = await run_in_threadpool(save_quote, user_email, item, quantity)
        logger.info(f"Devis créé : quote_id={quote_id}")
        pdf_path = f"quotes/quote_{quote_id}.pdf" # Obtenir le chemin après sauvegarde

        response_message = ""

        # Étape 2 : Si pas en stock, préparer une commande en attente
        if stock < quantity:
            await run_in_threadpool(save_pending_order, user_email, item, quantity)
            response_message = f"Devis #{quote_id} créé. Le stock étant insuffisant, nous avons mis votre commande en attente. Vous recevrez le devis par email."
            logger.info("Commande en attente enregistrée pour /order")
        # Étape 3 : Si en stock, préparer la commande et la livraison/retrait
        else:
            await run_in_threadpool(save_order, user_email, item, quantity, delivery_method)
            response_message = f"Devis #{quote_id} créé. Votre commande est prête pour {delivery_method}. Vous recevrez le devis par email pour validation."
            logger.info(f"Commande confirmée pour /order : delivery_method={delivery_method}")

        # Étape 4 : Envoyer le devis par email
        email_sent = await run_in_threadpool(send_quote_email, user_email, quote_id, pdf_path)
        if not email_sent:
            response_message += " (Note : l'envoi de l'email de devis a échoué.)"
        logger.info(f"Email de devis envoyé à {user_email} pour /order: {email_sent}")

        return {"message": response_message, "success": True, "quote_id": quote_id}

    except HTTPException as e:
        logger.error(f"HTTPException dans /order : {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Erreur inattendue dans /order : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la commande/devis : {random.choice(ERROR_MESSAGES)}")

@app.exception_handler(Exception)
async def custom_exception_handler(request, exc):
    logger.error(f"Erreur globale : {str(exc)}")
    return {"message": f"Catastrophe horticole ! Quelque chose a mal tourné : {random.choice(ERROR_MESSAGES)}"}