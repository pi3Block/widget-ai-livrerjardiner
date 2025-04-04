# Interface d'Administration (React-Admin)

Ce dossier contient le code source de l'interface d'administration de LivrerJardiner, construite avec React et [React-Admin](https://marmelab.com/react-admin/).

## Objectif

Fournir une interface web pour gérer les données principales de l'application (Produits, Catégories, Utilisateurs, Commandes, etc.) en interagissant avec l'API backend FastAPI.

## Technologies Principales

-   **React**: Bibliothèque JavaScript pour construire l'interface utilisateur.
-   **React-Admin**: Framework pour construire des applications B2B/admin au-dessus d'API REST/GraphQL.
-   **Vite**: Outil de build et serveur de développement rapide.
-   **TypeScript**: Langage de programmation.
-   **`ra-data-simple-rest`**: Data Provider pour connecter React-Admin à une API REST simple.

## Structure du Dossier (`src/admin/`)

-   **`main.tsx`**: Point d'entrée de l'application d'administration. Configure le composant `<Admin>` de React-Admin, le `dataProvider`, et définit les ressources.
-   **`components/`**: Contient les composants React spécifiques à chaque ressource gérée.
    -   `products.tsx`: Composants `ProductList`, `ProductEdit`, `ProductCreate`.
    -   `categories.tsx`: Composants `CategoryList`, `CategoryEdit`, `CategoryCreate`.
    -   *(D'autres fichiers seront ajoutés pour les autres ressources)*
-   **`types.ts`** (ou dans `src/shared/types`): Définitions TypeScript pour les données manipulées.
-   **`README.md`**: Ce fichier.

## Développement

Pour lancer l'interface d'administration en mode développement :

1.  Assurez-vous que le backend FastAPI est lancé (voir le `README.md` du backend).
2.  Exécutez la commande suivante à la racine du projet frontend :
    ```bash
    npm run dev
    ```
3.  Ouvrez l'URL fournie par Vite (généralement `http://localhost:5173`) dans votre navigateur.

## Ressources Actuellement Gérées

-   **Produits**: Listage, Création, Édition (informations de base + lien catégorie).
-   **Catégories**: Listage, Création, Édition.

## Prochaines Étapes (Voir `ROADMAP.md` à la racine)

-   Implémenter l'authentification (`authProvider`).
-   Ajouter la gestion CRUD pour d'autres ressources (Utilisateurs, Commandes...).
-   Améliorer la gestion des variations de produits dans les formulaires.
-   Affiner l'interface utilisateur (filtres, affichages spécifiques...).
