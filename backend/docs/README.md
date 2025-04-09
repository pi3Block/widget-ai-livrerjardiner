# Backend API - LivrerJardiner

Ce répertoire contient le backend de l'application LivrerJardiner, développé avec FastAPI.

## Description

Le backend fournit une API RESTful pour gérer les aspects suivants de l'application :

- **Produits et Variations** : Gestion du catalogue produits, incluant les différentes variations (taille, couleur, etc.), leur prix, stock, et attributs.
- **Utilisateurs et Authentification** : Enregistrement, connexion (via JWT), et gestion des profils utilisateurs.
- **Adresses** : Gestion des adresses de livraison et de facturation des utilisateurs.
- **Devis** : Création et consultation de devis multi-produits.
- **Commandes** : Création et consultation de commandes multi-produits, avec mise à jour transactionnelle du stock.
- **Stock** : Suivi du stock par variation de produit et historique des mouvements.
- **Chat IA** : Interaction avec un assistant IA (basé sur Ollama) pour répondre aux questions et potentiellement initier des actions (en cours d'adaptation pour V3).

## Technologies Utilisées

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Serveur ASGI**: [Uvicorn](https://www.uvicorn.org/)
- **Base de Données**: [PostgreSQL](https://www.postgresql.org/docs/)
- **ORM**: [SQLAlchemy](https://docs.sqlalchemy.org/en/20/) (utilisé en mode asynchrone)
- **Driver DB**: [psycopg2](https://www.psycopg.org/docs/) / psycopg2-binary (utilisé par SQLAlchemy)
- **Validation de Données**: [Pydantic v2](https://docs.pydantic.dev/)
- **Authentification**: JWT ([python-jose[cryptography]](https://python-jose.readthedocs.io/en/latest/))
- **Hachage de Mot de Passe**: [Passlib[bcrypt]](https://passlib.readthedocs.io/en/stable/)
- **Interaction LLM**: [Langchain](https://python.langchain.com/), [Langchain-Ollama](https://python.langchain.com/docs/integrations/llms/ollama)
- **Opérations CRUD**: [FastCRUD](https://igorbenav.github.io/fastcrud/) (*Note: Non détecté dans les imports scannés*)
- **Configuration**: [python-dotenv](https://github.com/theskumar/python-dotenv)

## Structure du Projet (backend/)

```
backend/
├── src/
│   ├── addresses/      # Module de gestion des adresses
│   ├── core/           # Configuration de base, sécurité, etc.
│   ├── database/       # Connexion et modèles ORM (si séparés)
│   ├── email/          # Logique d'envoi d'emails
│   ├── general_crud/   # (Vérifier utilité/renommer) Fonctions CRUD génériques ?
│   ├── llm/            # Intégration LLM (Ollama, Langchain)
│   ├── orders/         # Module de gestion des commandes
│   ├── pdf/            # Génération de PDF
│   ├── products/       # Module de gestion des produits, catégories, stock
│   ├── quotes/         # Module de gestion des devis
│   ├── users/          # Module de gestion des utilisateurs et authentification
│   └── main.py         # Point d'entrée FastAPI, routage principal
├── SQL/
│   └── table.sql       # Schéma SQL de la base de données (V3)
├── static/             # Fichiers statiques (si nécessaire)
├── .venv/              # Environnement virtuel Python (non versionné)
├── .env                # Fichier (à créer) pour les variables d'environnement (non versionné)
├── README.md           # Ce fichier
├── ROADMAP.md          # Feuille de route du développement
└── requirements.txt    # Dépendances Python
```

## Base de Données

Le backend utilise une base de données PostgreSQL. Le schéma actuel (V3) est défini dans `SQL/table.sql` et inclut des tables pour :

- `users`: Informations utilisateur et credentials.
- `addresses`: Adresses de livraison et facturation associées aux utilisateurs.
- `categories`: Catégories de produits (potentiellement hiérarchiques).
- `products`: Informations générales sur les produits.
- `product_variants`: Variations spécifiques d'un produit (taille, couleur, SKU, prix).
- `tags`: Tags applicables aux variations de produits.
- `product_variant_tags`: Table de liaison Many-to-Many entre variations et tags.
- `stock`: Quantité en stock pour chaque variation de produit.
- `orders`: En-tête des commandes clients.
- `order_items`: Lignes de détail des commandes.
- `stock_movements`: Historique des entrées/sorties de stock.
- `quotes`: En-tête des devis.
- `quote_items`: Lignes de détail des devis.

## Authentification

L'authentification est gérée via des tokens JWT (Bearer Tokens). 

- **Obtention du token**: Endpoint `POST /auth/token`. Celui-ci utilise `OAuth2PasswordRequestForm` et attend donc les identifiants (`username`, `password`) envoyés au format `application/x-www-form-urlencoded`.
- **Enregistrement**: Endpoint `POST /users/` (attend du JSON).
- **Protection des routes**: De nombreux endpoints nécessitent un token valide dans l'en-tête `Authorization: Bearer <token>`. La dépendance `Depends(auth.get_current_active_user)` est utilisée pour cela.

## Configuration

La configuration de l'application est gérée via des variables d'environnement, chargées depuis un fichier `.env` situé à la racine du répertoire `backend/`.

Créez un fichier `.env` basé sur les besoins (voir `config.py`) et définissez au minimum :

- `POSTGRES_USER=votre_user_db`
- `POSTGRES_PASSWORD=votre_mot_de_passe_db`
- `POSTGRES_DB=nom_db`
- `POSTGRES_HOST=localhost` (ou l'hôte de votre DB)
- `POSTGRES_PORT=5432` (ou le port de votre DB)
- `JWT_SECRET_KEY=votre_cle_secrete_jwt_tres_forte` (Générez une clé sécurisée, ex: `openssl rand -hex 32`)
- `OLLAMA_BASE_URL=http://localhost:11434` (si différent)
- `SENDER_EMAIL=` (si utilisation de l'envoi d'email)
- `SENDER_PASSWORD=` (si utilisation de l'envoi d'email)

**IMPORTANT : Ne commitez jamais votre fichier `.env` dans un dépôt Git.**

## Installation et Lancement

1.  **Prérequis**: Python 3.10+ et PostgreSQL installés et configurés.
2.  **Cloner le dépôt** (si ce n'est pas déjà fait).
3.  **Créer un environnement virtuel** (recommandé):
    ```bash
    python -m venv venv
    source venv/bin/activate # Linux/macOS
    # venv\Scripts\activate # Windows
    ```
4.  **Installer les dépendances**: Créez ou mettez à jour le fichier `requirements.txt`, puis :
    ```bash
    pip install -r requirements.txt 
    # Assurez-vous que les dépendances clés sont présentes: fastapi uvicorn "psycopg2-binary" python-dotenv "passlib[bcrypt]" "python-jose[cryptography]" langchain langchain_ollama
    # Une mise à jour de passlib peut être nécessaire : pip install --upgrade passlib
    ```
5.  **Créer et configurer le fichier `.env`** à la racine de `backend/` (voir section Configuration).
6.  **Appliquer le schéma de base de données**: Exécutez le script `SQL/table.sql` sur votre base de données PostgreSQL.
7.  **Lancer le serveur FastAPI** (depuis la racine du projet):
    ```bash
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
    ```
    Le serveur sera accessible sur `http://localhost:8000`.

## Endpoints API

L'API expose plusieurs endpoints organisés par ressource pour gérer les différentes fonctionnalités de l'application. Pour une documentation interactive complète et à jour, incluant les détails des paramètres, des corps de requête et des réponses, ainsi que la possibilité de tester les endpoints directement, accédez à l'interface Swagger UI générée automatiquement par FastAPI :

**`/docs`** (ex: `http://localhost:8000/docs`)

Voici un aperçu des principaux groupes d'endpoints basés sur les routeurs inclus :

- **`/auth`**: Authentification et gestion des tokens.
- **`/users`**: Enregistrement et gestion des informations utilisateur (dont `/users/me`).
- **`/addresses`**: Gestion des adresses pour l'utilisateur connecté.
- **`/products`**: Gestion des produits et de leurs variations.
- **`/categories`**: Gestion des catégories de produits.
- **`/tags`**: Gestion des tags associés aux produits.
- **`/stock`**: Consultation et gestion du stock des variations de produits.
- **`/quotes`**: Gestion des devis (création, consultation, mise à jour statut).
- **`/orders`**: Gestion des commandes (création, consultation, mise à jour statut).
- **`/llm`**: Interaction avec l'assistant IA (ex: `/llm/chat`).

**Note pour l'intégration React Admin (simpleRestProvider):** Les endpoints qui retournent des listes de ressources utilisées par React Admin (ex: `GET /products`, `GET /categories`) **doivent** inclure l'en-tête `Content-Range` dans leur réponse pour la pagination. Cet en-tête doit aussi être exposé via CORS (`expose_headers=["Content-Range"]`). Cela a été corrigé pour `/products` et `/categories`. Si `/quotes` ou `/orders` sont ajoutés comme ressources React Admin, leurs endpoints respectifs devront également être adaptés.

## État Actuel et Roadmap

Le backend a subi une refonte majeure (V3) pour supporter la structure de données actuelle. L'authentification utilisateur via JWT et l'affichage des listes principales (produits, catégories) dans l'interface d'administration sont désormais fonctionnels après correction des problèmes de formatage de requête et d'en-tête `Content-Range`.

La phase de tests et d'affinage continue (voir Étape 5 dans `ROADMAP.md`).

Consultez le fichier `ROADMAP.md` pour plus de détails sur les étapes de développement passées et futures.
