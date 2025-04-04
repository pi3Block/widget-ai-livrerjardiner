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
    *   [ ] **Identifier les entités** à gérer via l'interface d'administration :
        *   `users`
        *   `addresses`
        *   `categories`
        *   `tags`
        *   `products`
        *   `product_variants`
        *   `product_variant_tags` (Table de liaison)
        *   `stock`
        *   `stock_movements`
        *   `quotes`
        *   `quote_items`
        *   `orders`
        *   `order_items`
    *   [ ] **Pour chaque entité, définir une `<Resource>`** avec les vues associées (List, Edit, Create, Show si pertinent).
        *   [x] `products` (partiellement fait)
        *   [x] `categories` (partiellement fait)
        *   [ ] `users`
        *   [ ] `addresses`
        *   [ ] `tags`
        *   [ ] `product_variants`
        *   [ ] `stock`
        *   [ ] `stock_movements`
        *   [ ] `quotes`
        *   [ ] `quote_items`
        *   [ ] `orders`
        *   [ ] `order_items`
    *   [ ] **Remplacer les `Guesser`** par des composants spécifiques pour chaque ressource.

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
    *   [ ] **Gérer les relations** entre les entités (ex: `<ReferenceInput>`, `<ReferenceField>`, `<ReferenceManyField>`, `<ArrayInput>` pour many-to-many):
        *   [x] `Product` <-> `Category` (one-to-many)
        *   [ ] `Category` <-> `Category` (parent_category_id, self-reference)
        *   [ ] `Product` <-> `ProductVariant` (one-to-many)
        *   [ ] `ProductVariant` <-> `Tag` (many-to-many via `product_variant_tags`)
        *   [ ] `User` <-> `Address` (one-to-many)
        *   [ ] `User` <-> `Order` (one-to-many)
        *   [ ] `User` <-> `Quote` (one-to-many)
        *   [ ] `ProductVariant` <-> `Stock` (one-to-one ou one-to-many si gestion multi-entrepôts)
        *   [ ] `Stock` <-> `StockMovement` (one-to-many)
        *   [ ] `Quote` <-> `QuoteItem` (one-to-many)
        *   [ ] `Order` <-> `OrderItem` (one-to-many)
        *   [ ] `QuoteItem`/`OrderItem` <-> `ProductVariant` (many-to-one)
    *   [ ] **Gérer les types de données spécifiques** (ex: JSONB pour `attributes` dans `ProductVariant`, gestion des dates, des statuts enum).
    *   [ ] **Améliorer l'ergonomie** des formulaires et des listes (filtres, tris, champs affichés, vues conditionnelles).
    *   [ ] **Adapter le thème** si nécessaire.

6.  **Tests et Affinements**
    *   [ ] **Tester** le CRUD pour chaque ressource définie.
        *   [x] `products` (basique)
        *   [x] `categories` (basique)
        *   [ ] `users`
        *   [ ] `addresses`
        *   [ ] `tags`
        *   [ ] `product_variants`
        *   [ ] `stock`
        *   [ ] `stock_movements`
        *   [ ] `quotes`
        *   [ ] `quote_items`
        *   [ ] `orders`
        *   [ ] `order_items`
    *   [x] **Tester** le flux d'authentification (login/logout).
    *   [ ] **Tester** la gestion des relations et des types spécifiques.
    *   [ ] **Recueillir les retours** et affiner l'interface.
    *   [ ] **Vérifier** la gestion des erreurs (autres que 401/403).

*Ce document servira de guide pour le développement de l'interface d'administration.*
