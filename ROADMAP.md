# Roadmap Intégration React-Admin & FastAPI

**Objectif :** Mettre en place une interface d'administration (CRUD) fonctionnelle et robuste pour gérer les données de l'application via le backend FastAPI existant, en utilisant la bibliothèque React-Admin.

## Étapes Clés

1.  **Choix et Configuration du Data Provider**
    *   [x] **Évaluer les options :**
        *   `ra-data-simple-rest` : Conventions REST vérifiées et adaptées.
    *   [x] **Installer le Data Provider** (fait avec react-admin).
    *   [x] **Configurer le Data Provider** : Communication OK, gestion `Content-Range` ajoutée, `httpClient` personnalisé pour auth JWT.

2.  **Mise en Place de React-Admin**
    *   [x] **Installer `react-admin`** et ses dépendances.
    *   [x] **Créer le composant principal `<Admin>`** (`src/admin/main.tsx`).
    *   [x] **Intégrer le `dataProvider`** configuré.

3.  **Définition des Ressources CRUD**
    *   [x] **Identifier les entités** (`products`, `categories` principalement pour l'instant).
    *   [x] **Pour chaque entité, définir une `<Resource>`** (`products`, `categories`).
    *   [x] **Remplacer les `Guesser`** par des composants spécifiques (`ProductList/Edit/Create`, `CategoryList/Edit/Create`).

4.  **Implémentation de l'Authentification**
    *   [x] **Créer un `authProvider`** (`src/admin/authProvider.ts`).
    *   [x] **Implémenter les méthodes requises** :
        *   `login()`: OK (interaction avec `POST /auth/token` en `x-www-form-urlencoded`).
        *   `logout()`: OK (suppression token local).
        *   `checkAuth()`: OK (vérification token local).
        *   `checkError()`: OK (gestion 401/403 pour déconnexion).
        *   `getIdentity()`: OK (appel `GET /users/me`).
        *   `getPermissions()`: OK (basique).
    *   [x] **Intégrer l'`authProvider`**.
    *   [x] **Personnaliser la page de connexion** (label Email, bouton Créer compte).

5.  **Personnalisation de l'Interface Utilisateur**
    *   [ ] **Gérer les relations** entre les entités :
        *   [x] Clés étrangères (one-to-many) : `<ReferenceInput>` utilisé pour `category_id` dans `ProductCreate`.
        *   [ ] Vérifier `<ReferenceField>` dans les listes/éditions.
        *   [ ] Gérer la relation `parent_category_id` pour les catégories.
        *   [ ] Relations inversées (one-to-many) : `variants` dans `Product` ?
        *   [ ] Relations many-to-many : `tags` pour `ProductVariant` ?
    *   [ ] **Gérer les types de données spécifiques** (ex: JSONB pour `attributes` dans `ProductVariant`).
    *   [ ] **Améliorer l'ergonomie** des formulaires et des listes (filtres, tris, champs affichés).
    *   [ ] **Adapter le thème** si nécessaire.

6.  **Tests et Affinements**
    *   [x] **Tester** CRUD `products`, `categories` (basique).
    *   [x] **Tester** le flux d'authentification (login/logout).
    *   [ ] **Recueillir les retours** et affiner l'interface.
    *   [ ] **Vérifier** la gestion des erreurs (autres que 401/403).

*Ce document servira de guide pour le développement de l'interface d'administration.*
