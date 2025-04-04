import logging
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
# Importer la configuration
import config
from typing import Optional

logger = logging.getLogger(__name__)

# --- Initialisation des LLMs --- 
llms = {}

def initialize_llm(model_name: str):
    """Tente d'initialiser un modèle LLM via Ollama."""
    try:
        llm_instance = OllamaLLM(model=model_name, base_url=config.OLLAMA_BASE_URL)
        # Test rapide pour vérifier la connexion (optionnel mais recommandé)
        # llm_instance.invoke("ping") # Décommenter si invoke simple fonctionne
        logger.info(f"LLM '{model_name}' initialisé avec succès depuis {config.OLLAMA_BASE_URL}")
        return llm_instance
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du LLM '{model_name}' : {str(e)}")
        return None

# Initialiser Mistral (modèle par défaut)
llms["mistral"] = initialize_llm("mistral")

# Initialiser le modèle Meta (LLaMA)
if config.META_MODEL_NAME:
    llms[config.META_MODEL_NAME] = initialize_llm(config.META_MODEL_NAME)

# --- Définition des Prompts ---

# Prompt principal pour les réponses après vérification du stock d'une variation
stock_prompt = PromptTemplate(
    input_variables=["input", "stock", "quantity", "sku", "is_enough"],
    template="L'utilisateur demande : {input}. Pour le produit avec référence (SKU) {sku}, le stock actuel est de {stock} unités pour une demande de {quantity}. Le stock est-il suffisant ? {is_enough}. Réponds de manière utile et conviviale, en français uniquement. Si le stock est insuffisant, indique la quantité disponible."
)

# Prompt simple pour la conversation générale
general_chat_prompt = PromptTemplate(
    input_variables=["input"],
    template="L'utilisateur demande : {input}. Réponds de manière utile, conviviale et pertinente pour un assistant de site e-commerce de jardinage, en français uniquement."
)

# Prompt pour le parsing initial (Intent + Entities V3)
parsing_prompt_template = """Analyse la demande de l'utilisateur suivante et retourne un objet JSON valide.
Le JSON doit contenir une clé principale "intent" et une clé "items" qui est une liste d'objets.

Intentions possibles pour la clé "intent":
- "demande_produits": L'utilisateur demande des informations sur un ou plusieurs produits, leur stock, leur prix, etc.
- "creer_devis": L'utilisateur exprime clairement l'intention de recevoir un devis pour les produits mentionnés.
- "passer_commande": L'utilisateur veut acheter/commander les produits mentionnés (peut nécessiter des étapes supplémentaires).
- "info_generale": Question générale sur le jardinage, l'entreprise, etc.
- "salutation": Simple bonjour, merci, etc.

Chaque objet dans la liste "items" doit contenir:
- "sku": La référence exacte du produit (Stock Keeping Unit, ex: "ROS-RED-M", "POT-TER-10L") si elle est explicitement mentionnée ou clairement déductible.
- "base_product": Le nom générique du produit (ex: "rosier", "pot terre cuite") si le SKU n'est pas trouvé.
- "attributes": Un objet JSON contenant les attributs spécifiés (ex: {{"taille": "M", "couleur": "rouge"}}) si le SKU n'est pas trouvé.
- "quantity": Le nombre entier demandé (défaut à 1 si non spécifié mais intention d'achat/devis claire).

Si la demande est générale et ne mentionne aucun produit spécifique, la liste "items" peut être vide ou absente.
Priorise l'extraction du "sku". Si le SKU n'est pas clair mais que des attributs sont donnés, extrais "base_product" et "attributes".
Si plusieurs produits sont mentionnés, ajoute un objet pour chacun dans la liste "items".
Ne retourne que le JSON, sans texte explicatif avant ou après, et sans utiliser de blocs de code markdown.

Demande Utilisateur: "{input}"

JSON:
"""
parsing_prompt = PromptTemplate(input_variables=["input"], template=parsing_prompt_template)

# --- Fonction pour obtenir le LLM --- 
def get_llm(model_name: str = "mistral") -> Optional[OllamaLLM]:
    """Retourne l'instance LLM demandée, ou Mistral par défaut, ou None si indisponible."""
    # Utiliser le nom Meta configuré si demandé
    if model_name.lower() == "meta":
        model_name = config.META_MODEL_NAME
        
    selected_llm = llms.get(model_name)
    if selected_llm:
        return selected_llm
    # Si le modèle demandé n'est pas dispo, fallback sur mistral si possible
    fallback_llm = llms.get("mistral")
    if fallback_llm:
        logger.warning(f"Modèle '{model_name}' non disponible, fallback sur 'mistral'.")
        return fallback_llm
    logger.error(f"Aucun modèle LLM disponible (ni '{model_name}', ni 'mistral').")
    return None
