from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import psycopg2
from psycopg2 import OperationalError, ProgrammingError
import random
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

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
    "Erreur 404 : Rosiers introuvables... ou peut-être qu’ils se sont enfuis ?",
    "Notre base de données fait la sieste. On la réveille avec un café !",
]

try:
    llm = OllamaLLM(model="mistral", base_url="http://localhost:11434")
except Exception as e:
    llm = None

def check_stock(item: str) -> int:
    try:
        conn = psycopg2.connect(dbname="livrerjardiner", user="monuser", password="moncode")
        cur = conn.cursor()
        cur.execute("SELECT quantity FROM stock WHERE item=%s", (item,))
        result = cur.fetchone()
        conn.close()
        return result[0] if result else 0
    except OperationalError:
        raise HTTPException(status_code=503, detail=random.choice(ERROR_MESSAGES))
    except ProgrammingError:
        raise HTTPException(status_code=500, detail="Le jardinier a planté la requête SQL... On creuse pour réparer !")

def parse_input(input: str) -> tuple[str, int]:
    match = re.search(r"(\d+)\s*(\w+)", input.lower())
    if match:
        quantity = int(match.group(1))
        item = match.group(2)
        return item, quantity
    if "stock" in input.lower():
        item = input.lower().replace("stock de", "").strip()
        return item, 1
    return "rosiers", 10

def generate_quote_pdf(item: str, quantity: int, unit_price: float, total_price: float, quote_id: int) -> str:
    pdf_path = f"quotes/quote_{quote_id}.pdf"
    os.makedirs("quotes", exist_ok=True)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, "Devis - LivrerJardiner.fr")
    c.drawString(100, 730, f"Devis #{quote_id}")
    c.drawString(100, 700, f"Article : {item}")
    c.drawString(100, 680, f"Quantité : {quantity}")
    c.drawString(100, 660, f"Prix unitaire : {unit_price} €")
    c.drawString(100, 640, f"Total : {total_price} €")
    c.drawString(100, 600, "Merci de valider ce devis pour confirmer votre commande.")
    c.save()
    return pdf_path

def save_quote(user_email: str, item: str, quantity: int) -> int:
    unit_price = 5.0  # Exemple : 5€ par article (à ajuster selon ta logique)
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
        return quote_id
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création du devis : {str(e)}")

def save_pending_order(user_email: str, item: str, quantity: int):
    try:
        conn = psycopg2.connect(dbname="livrerjardiner", user="monuser", password="moncode")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO pending_orders (user_email, item, quantity) VALUES (%s, %s, %s)",
            (user_email, item, quantity)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la commande en attente : {str(e)}")

def save_order(user_email: str, item: str, quantity: int, delivery_method: str):
    try:
        conn = psycopg2.connect(dbname="livrerjardiner", user="monuser", password="moncode")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO orders (user_email, item, quantity, delivery_method) VALUES (%s, %s, %s, %s)",
            (user_email, item, quantity, delivery_method)
        )
        # Mettre à jour le stock
        cur.execute("UPDATE stock SET quantity = quantity - %s WHERE item=%s", (quantity, item))
        conn.commit()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la commande : {str(e)}")

def send_quote_email(user_email: str, quote_id: int, pdf_path: str):
    sender_email = "tonemail@livrerjardiner.fr"
    sender_password = "tonmotdepasse"  # À sécuriser (utilise des variables d’environnement)
    subject = f"Devis #{quote_id} - LivrerJardiner.fr"
    body = f"""
    Bonjour,

    Voici votre devis #{quote_id} pour votre commande. Veuillez le valider pour confirmer.

    Merci de votre confiance,
    L’équipe LivrerJardiner.fr
    """

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = user_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Attacher le PDF
    with open(pdf_path, "rb") as f:
        attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header("Content-Disposition", "attachment", filename=f"devis_{quote_id}.pdf")
        msg.attach(attach)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)  # À ajuster selon ton service email
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, user_email, msg.as_string())
        server.quit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l’envoi de l’email : {str(e)}")

prompt = PromptTemplate(
    input_variables=["input", "stock", "quantity", "item", "is_enough"],
    template="L’utilisateur demande : {input}. Le stock actuel est de {stock} {item} pour une demande de {quantity}. Le stock est-il suffisant ? {is_enough}. Réponds de manière utile et conviviale."
)

if llm:
    chain = prompt | llm
else:
    chain = None

@app.get("/chat")
async def chat(input: str, user_email: str, delivery_method: str = "livraison"):
    if not chain:
        return {"message": "Désolé, notre assistant IA est en grève pour plus de soleil ! Réessaie plus tard."}

    # Étape 1 : Accueillir et parser le besoin
    item, quantity = parse_input(input)

    try:
        # Étape 2 : Vérifier le stock
        stock = check_stock(item)
        is_enough = "Oui" if stock >= quantity else "Non"
        response = chain.invoke({
            "input": input,
            "stock": stock,
            "quantity": quantity,
            "item": item,
            "is_enough": is_enough
        })

        # Étape 3 : Créer un devis
        quote_id = save_quote(user_email, item, quantity)

        # Étape 4 : Si pas en stock, préparer une commande en attente
        if stock < quantity:
            save_pending_order(user_email, item, quantity)
            response += " Comme le stock est insuffisant, nous avons mis votre commande en attente. Vous recevrez un devis par email."

        # Étape 5 : Si en stock, préparer la commande et la livraison/retrait
        else:
            save_order(user_email, item, quantity, delivery_method)
            response += f" Votre commande est prête pour {delivery_method}. Vous recevrez un devis par email pour validation."

        # Étape 6 : Envoyer le devis par email
        pdf_path = f"quotes/quote_{quote_id}.pdf"
        send_quote_email(user_email, quote_id, pdf_path)

        return {"message": response}
    except HTTPException as e:
        raise e
    except Exception:
        return {"message": f"Oups, l’IA a renversé son terreau : {random.choice(ERROR_MESSAGES)}"}

@app.exception_handler(Exception)
async def custom_exception_handler(request, exc):
    return {"message": f"Catastrophe horticole ! Quelque chose a mal tourné : {random.choice(ERROR_MESSAGES)}"}