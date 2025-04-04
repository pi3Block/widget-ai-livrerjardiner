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

# Prompt pour le parsing initial (Intent + Entities)
parsing_prompt_template = """Analyse la demande de l'utilisateur suivante et retourne un objet JSON valide avec les clés "intent" et "entities".
Les intents possibles sont: "verifier_stock", "demande_quantite", "info_generale".
Les entités possibles dans l'objet "entities" sont: "item" (le nom normalisé de l'article, en minuscule et singulier si possible) et "quantity" (le nombre entier demandé).
Si une entité n'est pas trouvée ou non applicable, retourne null pour sa valeur ou omet la clé. Ne retourne que le JSON, sans texte explicatif avant ou après.

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
