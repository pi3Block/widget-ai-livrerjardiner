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
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from dotenv import load_dotenv
from typing import Optional
from pydantic import BaseModel, EmailStr
import time

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
        Sends an email to the specified recipient
        """
        raw = MIMEText(message)
        raw["Subject"] = subject
        raw["From"] = sender
        raw["To"] = recipient

        if self.conn:
            try:
                self.conn.sendmail(sender, recipient, raw.as_string())
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
            self.conn.quit()
            self.conn = None
            logger.debug("Connexion SMTP fermée")

# Initialiser le client SMTP Hostinger
smtp_client = SMTPHostinger()
if not smtp_client.auth(sender_email, sender_password, smtp_host, smtp_port, debug=True):
    logger.error("Échec de l'authentification SMTP au démarrage")

# Reste du code (check_stock, parse_input, etc.) reste inchangé
def check_stock(item: str) -> int:
    logger.debug(f"Vérification du stock pour l'article : {item}")
    try:
        conn = psycopg2.connect(dbname="livrerjardiner", user="monuser", password="moncode")
        cur = conn.cursor()
        cur.execute("SELECT quantity FROM stock WHERE item=%s", (item,))
        result = cur.fetchone()
        conn.close()
        stock = result[0] if result else 0
        logger.debug(f"Stock trouvé : {stock}")
        return stock
    except OperationalError as e:
        logger.error(f"Erreur opérationnelle lors de la vérification du stock : {str(e)}")
        raise HTTPException(status_code=503, detail=random.choice(ERROR_MESSAGES))
    except ProgrammingError as e:
        logger.error(f"Erreur de programmation lors de la vérification du stock : {str(e)}")
        raise HTTPException(status_code=500, detail="Le jardinier a planté la requête SQL... On creuse pour réparer !")

def parse_input(input: str) -> tuple[str, int]:
    logger.debug(f"Parsing de l'input : {input}")
    match = re.search(r"(\d+)\s*(\w+)", input.lower())
    if match:
        quantity = int(match.group(1))
        item = match.group(2)
        logger.debug(f"Input parsé : item={item}, quantity={quantity}")
        return item, quantity
    if "stock" in input.lower():
        item = input.lower().replace("stock de", "").strip()
        logger.debug(f"Input parsé (stock) : item={item}, quantity=1")
        return item, 1
    logger.debug("Input non reconnu, valeurs par défaut : item=rosiers, quantity=10")
    return "rosiers", 10

def generate_quote_pdf(item: str, quantity: int, unit_price: float, total_price: float, quote_id: int) -> str:
    logger.debug(f"Génération du PDF pour le devis #{quote_id}")
    pdf_path = f"quotes/quote_{quote_id}.pdf"
    try:
        os.makedirs("quotes", exist_ok=True)
        logger.debug(f"Dossier quotes créé ou existant")
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, "Devis - LivrerJardiner.fr")
        c.drawString(100, 730, f"Devis #{quote_id}")
        c.drawString(100, 700, f"Article : {item}")
        c.drawString(100, 680, f"Quantité : {quantity}")
        c.drawString(100, 660, f"Prix unitaire : {unit_price} €")
        c.drawString(100, 640, f"Total : {total_price} €")
        c.drawString(100, 600, "Merci de valider ce devis pour confirmer votre commande.")
        c.save()
        logger.debug(f"PDF généré : {pdf_path}")
        return pdf_path
    except Exception as e:
        logger.error(f"Erreur lors de la génération du PDF : {str(e)}")
        raise

def save_quote(user_email: str, item: str, quantity: int) -> int:
    logger.debug(f"Sauvegarde du devis pour {user_email}, item={item}, quantity={quantity}")
    unit_price = 5.0  # Exemple : 5€ par article
    total_price = unit_price * quantity
    try:
        conn = psycopg2.connect(dbname="livrerjardiner", user="monuser", password="moncode")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO quotes (user_email, item, quantity, unit_price, total_price) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (user_email, item, quantity, unit_price, total_price)
        )
        quote_id = cur.fetchone()[0]
        pdf_path = generate_quote_pdf(item, quantity, unit_price, total_price, quote_id)
        cur.execute("UPDATE quotes SET pdf_path=%s WHERE id=%s", (pdf_path, quote_id))
        conn.commit()
        conn.close()
        logger.debug(f"Devis sauvegardé : quote_id={quote_id}")
        return quote_id
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du devis : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du devis : {str(e)}")

def save_pending_order(user_email: str, item: str, quantity: int):
    logger.debug(f"Sauvegarde d'une commande en attente pour {user_email}, item={item}, quantity={quantity}")
    try:
        conn = psycopg2.connect(dbname="livrerjardiner", user="monuser", password="moncode")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO pending_orders (user_email, item, quantity) VALUES (%s, %s, %s)",
            (user_email, item, quantity)
        )
        conn.commit()
        conn.close()
        logger.debug("Commande en attente sauvegardée")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de la commande en attente : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la commande en attente : {str(e)}")

def save_order(user_email: str, item: str, quantity: int, delivery_method: str):
    logger.debug(f"Sauvegarde de la commande pour {user_email}, item={item}, quantity={quantity}, delivery_method={delivery_method}")
    try:
        conn = psycopg2.connect(dbname="livrerjardiner", user="monuser", password="moncode")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO orders (user_email, item, quantity, delivery_method) VALUES (%s, %s, %s, %s)",
            (user_email, item, quantity, delivery_method)
        )
        cur.execute("UPDATE stock SET quantity = quantity - %s WHERE item=%s", (quantity, item))
        conn.commit()
        conn.close()
        logger.debug("Commande sauvegardée et stock mis à jour")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de la commande : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la commande : {str(e)}")

def send_quote_email(user_email: str, quote_id: int, pdf_path: str):
    logger.debug(f"Envoi de l'email à {user_email} pour le devis #{quote_id}")
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
        logger.error(f"Erreur lors de la lecture du PDF pour l'email : {str(e)}")
        raise

    # Utiliser SMTPHostinger pour envoyer l'email
    email_sent = smtp_client.send(
        recipient=user_email,
        sender=sender_email,
        subject=subject,
        message=msg.as_string()
    )
    if not email_sent:
        logger.error("Échec de l'envoi de l'email")
    return email_sent

try:
    llm = OllamaLLM(model="mistral", base_url="http://localhost:11434")
    logger.info("LLM initialisé avec succès")
except Exception as e:
    logger.error(f"Erreur lors de l'initialisation du LLM : {str(e)}")
    llm = None

prompt = PromptTemplate(
    input_variables=["input", "stock", "quantity", "item", "is_enough"],
    template="L'utilisateur demande : {input}. Le stock actuel est de {stock} {item} pour une demande de {quantity}. Le stock est-il suffisant ? {is_enough}. Réponds de manière utile et conviviale."
)

if llm:
    chain = prompt | llm
else:
    chain = None

@app.get("/chat")
async def chat(input: str, delivery_method: str = "livraison", user_email: Optional[str] = None):
    logger.info(f"Requête chat reçue : input={input}, user_email={user_email}, delivery_method={delivery_method}")
    if not chain:
        logger.error("LLM non disponible")
        return {"message": "Désolé, notre assistant IA est en grève pour plus de soleil ! Réessaie plus tard.", "can_order": False, "item": "", "quantity": 0}

    # Étape 1 : Accueillir et parser le besoin
    item, quantity = parse_input(input)
    logger.info(f"Input parsé : item={item}, quantity={quantity}")

    # Préparer les données pour le retour
    return_data = {
        "message": "",
        "can_order": False,
        "item": item,
        "quantity": quantity
    }

    try:
        # Étape 2 : Vérifier le stock
        stock = check_stock(item)
        logger.info(f"Stock vérifié : stock={stock}")
        is_enough = "Oui" if stock >= quantity else "Non"

        # Générer la réponse conversationnelle du LLM
        response = chain.invoke({
            "input": input,
            "stock": stock,
            "quantity": quantity,
            "item": item,
            "is_enough": is_enough
        })
        logger.info(f"Réponse LLM : {response}")

        return_data["message"] = response

        # Déterminer si une commande est possible (pour le bouton Commander)
        if stock >= quantity:
             return_data["can_order"] = True
             # Optionnel : Ajouter un indice dans le message si stock suffisant
             # return_data["message"] += " Nous avons cela en stock !"

        # --- LOGIQUE DE COMMANDE/DEVIS/EMAIL SUPPRIMÉE ICI ---

        return return_data # Retourner le message et les infos pour le frontend

    except HTTPException as e:
        logger.error(f"HTTPException dans /chat : {str(e)}")
        return {"message": e.detail, "can_order": False, "item": item, "quantity": quantity}
    except Exception as e:
        logger.error(f"Erreur inattendue dans /chat : {str(e)}")
        error_msg = random.choice(ERROR_MESSAGES)
        return {"message": f"Oups, l'IA a renversé son terreau : {error_msg}", "can_order": False, "item": item, "quantity": quantity}

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
        stock = check_stock(item)
        logger.info(f"Stock vérifié pour la commande : stock={stock}")

        # --- LOGIQUE DE COMMANDE/DEVIS/EMAIL DÉPLACÉE ICI ---
        # Étape 1 : Créer un devis
        quote_id = save_quote(user_email, item, quantity)
        logger.info(f"Devis créé : quote_id={quote_id}")
        pdf_path = f"quotes/quote_{quote_id}.pdf" # Obtenir le chemin après sauvegarde

        response_message = ""

        # Étape 2 : Si pas en stock, préparer une commande en attente
        if stock < quantity:
            save_pending_order(user_email, item, quantity)
            response_message = f"Devis #{quote_id} créé. Le stock étant insuffisant, nous avons mis votre commande en attente. Vous recevrez le devis par email."
            logger.info("Commande en attente enregistrée pour /order")
        # Étape 3 : Si en stock, préparer la commande et la livraison/retrait
        else:
            save_order(user_email, item, quantity, delivery_method)
            response_message = f"Devis #{quote_id} créé. Votre commande est prête pour {delivery_method}. Vous recevrez le devis par email pour validation."
            logger.info(f"Commande confirmée pour /order : delivery_method={delivery_method}")

        # Étape 4 : Envoyer le devis par email
        email_sent = send_quote_email(user_email, quote_id, pdf_path)
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

# Fermer la connexion SMTP à la fermeture de l'application
@app.on_event("shutdown")
def shutdown_event():
    smtp_client.close()