# Module LLM

Ce module gère les interactions avec les modèles de langage (LLM) pour le site LivrerJardiner.

## Structure du Module

Le module suit une architecture en couches avec séparation claire des responsabilités :

```
llm/
├── application/           # Couche application
│   ├── llm_service.py     # Service pour la gestion des requêtes LLM
│   └── services.py        # Service de chat utilisant le LLM
├── domain/                # Couche domaine
│   ├── exceptions.py      # Exceptions spécifiques au domaine
│   └── llm_interface.py   # Interface pour les clients LLM
├── infrastructure/        # Couche infrastructure
│   ├── ollama_client.py   # Client pour Ollama
│   └── openai_client.py   # Client pour OpenAI
├── interfaces/            # Couche interfaces
│   └── api.py             # API FastAPI
├── config.py              # Configuration locale
├── constants.py           # Constantes
├── dependencies.py        # Dépendances FastAPI
├── models.py              # Modèles et schémas
├── router.py              # Routes FastAPI
├── templates.py           # Templates de prompts
└── utils.py               # Utilitaires
```

## Fonctionnalités

- **Gestion des requêtes LLM** : Création, récupération et traitement des requêtes LLM
- **Service de chat** : Interaction avec l'utilisateur via le LLM
- **Parsing d'intentions** : Analyse des demandes utilisateur pour extraire les intentions et entités
- **Intégration avec d'autres services** : Interaction avec les services de produits, commandes, devis, etc.

## Utilisation

### Service LLM

```python
from src.llm.application.llm_service import LLMService
from src.llm.models import LLMRequestBase

# Créer une requête LLM
request_data = LLMRequestBase(
    prompt="Quelle est la capitale de la France ?",
    model="gpt-3.5-turbo"
)

# Traiter la requête
llm_service = LLMService(db_session)
request = llm_service.create_request(request_data, user_id=1)
result = llm_service.process_request(request.id)
```

### Service de Chat

```python
from src.llm.application.services import ChatService

# Créer un service de chat
chat_service = ChatService(
    llm=llm_client,
    variant_repo=variant_repository,
    stock_repo=stock_repository,
    quote_service=quote_service,
    email_service=email_service,
    pdf_service=pdf_service,
    order_service=order_service
)

# Gérer une demande utilisateur
response = await chat_service.handle_chat(
    user_input="Je cherche un rosier rouge",
    current_user=user,
    selected_model="gpt-3.5-turbo"
)
```

## Templates de Prompts

Les templates de prompts sont définis dans `templates.py` et sont utilisés pour formater les prompts envoyés au LLM.

## Exceptions

Les exceptions spécifiques au domaine LLM sont définies dans `domain/exceptions.py`.

## Configuration

La configuration du module est définie dans `config.py` et peut être personnalisée via des variables d'environnement. 