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

- **Framework**: FastAPI
- **Serveur ASGI**: Uvicorn
- **Base de Données**: PostgreSQL
- **Driver DB**: psycopg2 / psycopg2-binary
- **Validation de Données**: Pydantic v2
- **Authentification**: JWT (python-jose[cryptography])
- **Hachage de Mot de Passe**: Passlib[bcrypt]
- **Interaction LLM**: Langchain, Langchain-Ollama
- **Configuration**: python-dotenv

## Structure du Projet (backend/)

```
backend/
├── SQL/
│   └── table.sql           # Schéma SQL de la base de données (V3)
├── auth.py                 # Logique d'authentification JWT, dépendances FastAPI
├── config.py               # Chargement et gestion de la configuration (via .env)
├── crud.py                 # Fonctions d'accès et de modification de la base de données (CRUD)
├── llm_logic.py            # Logique et prompts pour l'interaction avec les LLMs (Ollama)
├── main.py                 # Point d'entrée de l'application FastAPI, définition des endpoints API
├── models.py               # Modèles Pydantic pour la validation des données et les réponses API
├── pdf_utils.py            # Utilitaires pour la génération de PDF (ex: devis)
├── services.py             # Services externes (ex: envoi d'email)
├── utils.py                # Fonctions utilitaires diverses
├── .env                    # Fichier (à créer) pour les variables d'environnement (secrets)
├── README.md               # Ce fichier
├── ROADMAP.md              # Feuille de route du développement
└── requirements.txt        # Fichier (à créer/gérer) listant les dépendances Python
```

## Base de Données

Le backend utilise une base de données PostgreSQL. Le schéma actuel (V3) est défini dans `SQL/table.sql` et inclut des tables pour :

- `users`, `addresses`
- `categories`, `tags`, `products`, `product_variants`, `product_variant_tags`
- `stock`, `stock_movements`
- `quotes`, `quote_items`
- `orders`, `order_items`

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

L'API expose plusieurs endpoints pour gérer les différentes ressources. Pour une documentation interactive complète et la possibilité de tester les endpoints directement, accédez à l'interface Swagger UI générée par FastAPI :

**`/docs`** (ex: `http://localhost:8000/docs`)

Principaux groupes d'endpoints disponibles :

- `/auth/token` : Connexion utilisateur.
- `/users/` : Enregistrement utilisateur.
- `/users/me` : Informations sur l'utilisateur connecté.
- `/users/me/addresses` : Gestion des adresses de l'utilisateur.
- `/products/` : Listage et filtrage des produits/variations.
- `/categories/` : Listage des catégories.
- `/quotes/` : Gestion des devis.
- `/orders/` : Gestion des commandes.
- `/chat` : Interaction avec l'assistant IA.

**Note pour l'intégration React Admin (simpleRestProvider):** Les endpoints qui retournent des listes de ressources utilisées par React Admin (ex: `GET /products`, `GET /categories`) **doivent** inclure l'en-tête `Content-Range` dans leur réponse pour la pagination. Cet en-tête doit aussi être exposé via CORS (`expose_headers=["Content-Range"]`). Cela a été corrigé pour `/products` et `/categories`. Si `/quotes` ou `/orders` sont ajoutés comme ressources React Admin, leurs endpoints respectifs devront également être adaptés.

## État Actuel et Roadmap

Le backend a subi une refonte majeure (V3) pour supporter la structure de données actuelle. L'authentification utilisateur via JWT et l'affichage des listes principales (produits, catégories) dans l'interface d'administration sont désormais fonctionnels après correction des problèmes de formatage de requête et d'en-tête `Content-Range`.

La phase de tests et d'affinage continue (voir Étape 5 dans `ROADMAP.md`).

Consultez le fichier `ROADMAP.md` pour plus de détails sur les étapes de développement passées et futures.
