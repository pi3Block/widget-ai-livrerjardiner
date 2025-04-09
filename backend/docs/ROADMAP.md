# Roadmap : Intégration catalogue, gestion stock et fonctionnalités avancées pour `livrerjardiner.fr`

Ce document recense les étapes nécessaires à l'intégration d'un catalogue étendu dans l'application `livrerjardiner.fr`, la gestion intelligente du stock, et l'optimisation de l'agent IA.

---

### Objectif global
- Intégrer un catalogue de produits de jardinage (~1000 références) avec variations (taille, couleur...).
- Gérer des comptes utilisateurs complets (profil, adresses, historique).
- Permettre des commandes multi-produits et des devis.
- Mettre en place une gestion du stock par variation de produit (alertes, historique, réapprovisionnement).
- Améliorer la recherche et le filtrage via des catégories et tags.
- Optimiser l'agent IA pour qu'il gère efficacement les variations et les commandes complexes, potentiellement via RAG.

### Contexte Technique
- Base de données : PostgreSQL.
- Backend : FastAPI (avec intégration prévue de **FastCRUD** pour simplifier les opérations de base), LLMs (Mistral/LLaMA 3 via Ollama).
- Frontend : React.
- Serveur : `piair@piairBig`.

---

## Étapes Clés

### 1. Refonte Majeure de la Base de Données et Adaptation du Backend
- **Objectif** : Mettre en place la structure de données V3 pour supporter toutes les fonctionnalités cibles (variations, multi-produits, utilisateurs, etc.) et adapter le backend en conséquence.
- **Statut** : **En cours de finalisation / Refactoring**
- **Actions réalisées/en cours** :
    - Structure Base de Données (SQL V3) : **FAIT**.
    - Adaptation Modèles SQLAlchemy (`database/models.py`) : **FAIT**.
    - Adaptation Schémas Pydantic (`application/schemas.py`) : **FAIT**.
    - **[EN COURS]** Refactoring de la couche d'accès aux données (`infrastructure/persistence.py`) et des services (`application/services.py`) pour :
        - **Utiliser FastCRUD** pour les opérations CRUD standard (Catégories, Tags, potentiellement Adresses, etc.).
        - Conserver/adapter des méthodes de repository manuelles uniquement pour la logique complexe non couverte par FastCRUD (ex: certaines jointures complexes, logique métier spécifique dans les requêtes).
    - Mise à jour des endpoints FastAPI (`interfaces/api.py`) pour utiliser les services refactorés : **EN COURS**.
    - Adaptation basique logique LLM (Prompts) : **FAIT**.
- **Points d'attention** :
    - Assurer la cohérence entre les modèles DB, les schémas Pydantic et les appels FastCRUD/repository.
    - Valider le bon fonctionnement des endpoints après refactoring.

### 2. Test Complet de l'Application
- **Objectif** : Vérifier que tout fonctionne correctement après la refonte et l'intégration de FastCRUD.
- **Statut** : **Prochaine étape majeure** (après finalisation Étape 1)
- **Actions à réaliser** :
    - Tester les endpoints `/auth`, `/users`, `/users/me/addresses`.
    - Tester l'endpoint `/products` (y compris variations) avec filtres et pagination.
    - Tester les endpoints `/categories`, `/tags`.
    - Tester les endpoints `/quotes` (créer, lister, get, MAJ statut).
    - Tester les endpoints `/orders` (créer, lister, get, MAJ statut) -> Vérifier impact DB (stock, mouvements).
    - Tester l'endpoint `/chat` avec des demandes incluant des variations SKU.
    - Surveiller les logs FastAPI et PostgreSQL pendant les tests.
    - Tests Frontend (par l'utilisateur/équipe frontend).
- **Points d'attention** :
    - Scénarios de tests variés couvrant les cas d'usage CRUD et la logique métier.

### 3. Optimisation des Performances
- **Objectif** : Assurer la réactivité de l'application.
- **Statut** : **À faire** (après tests V3)
- **Actions à réaliser** :
    - Cache Redis (pour données fréquemment accédées).
    - Optimisation des Requêtes SQL (via analyse `EXPLAIN` si nécessaire, surtout pour les requêtes complexes restantes).
    - Optimisation des Images (côté frontend/stockage).

### 4. Fonctionnalités Avancées et Interface d'Administration
- **Objectif** : Fournir des outils de gestion et améliorer l'expérience utilisateur et IA.
- **Statut** : **À faire** (après optimisation)
- **Actions à réaliser** :
    - Interface d'Administration (React Admin, FastAPI Admin, ou autre).
    - Recherche Avancée (potentiellement Elasticsearch ou via des fonctionnalités PostgreSQL avancées).
    - Système de Recommandations Produits.
    - Amélioration Agent IA via RAG (Base de connaissances externe, Vector Store, etc.).
    - Logique avancée `/chat` (gestion panier, etc.).

### 5. Surveillance et Maintenance Continue
- **Objectif** : Assurer la stabilité et la scalabilité.
- **Actions à réaliser** :
  - Monitoring (Prometheus, Grafana...).
  - Sauvegardes DB (`pg_dump`).
  - Mises à jour de sécurité.
  - Surveillance DB (taille, index).

---

## Résumé pour un LLM

**Contexte** : Application `livrerjardiner.fr` (FastAPI/PostgreSQL/React) gérant catalogue produits avec variations, utilisateurs, commandes/devis. Objectif ~1000 références.

**État Actuel** : Structure DB V3 en place. Backend en cours de refactoring pour utiliser **FastCRUD** pour les opérations CRUD standard et finaliser l'adaptation à la V3.

**Prochaine Étape Majeure (Étape 2 - Tests)** :
- Tester de manière exhaustive tous les endpoints API une fois le refactoring backend (Étape 1) terminé.

**Étapes Suivantes (Post-Tests)** :
- **Étape 3 : Optimisation** (Cache, SQL, Images).
- **Étape 4 : Fonctionnalités Avancées** (Admin, Recherche, RAG, Chat+).
- **Étape 5 : Maintenance**.

**Recommandations Immédiates** : Finaliser le **Refactoring Backend (Étape 1)** en intégrant FastCRUD pour simplifier le code CRUD. Tester rigoureusement ensuite (Étape 2).