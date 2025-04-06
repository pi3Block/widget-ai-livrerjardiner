# Widget AI LivrerJardiner & Interface d'Administration

Ce projet contient :
1.  Un **widget React interactif** conçu pour être intégré sur des sites web. Il permet aux utilisateurs d'interagir avec un chatbot IA pour obtenir des informations et potentiellement passer des commandes.
2.  Une **interface d'administration** (basée sur React-Admin, en cours de développement) pour gérer les données via une API backend (FastAPI).

Le projet utilise **Vite** comme outil de build et de développement.

## Structure du Code

-   **`/` (Racine)**:
    -   `index.html`: Point d'entrée HTML pour l'application d'administration (SPA).
    -   `vite.config.ts`: Configuration de Vite pour gérer les builds séparés de l'admin et du widget.
    -   `package.json`: Dépendances et scripts npm.
    -   `tsconfig.json`: Configuration TypeScript.
-   **`public/`**: Fichiers statiques.
-   **`src/`**: Code source principal.
    -   `admin/`: Code spécifique à l'interface d'administration.
        -   `main.tsx`: Point d'entrée Javascript/TypeScript pour l'admin (chargé par `index.html`).
        -   *(Autres composants et logique de l'admin...)*
    -   `widget/`: Code spécifique au widget.
        -   `Widget.tsx`: Composant React principal du widget.
        -   `Widget.css`: Styles du widget.
    -   `widget-entry.tsx`: Point d'entrée Javascript/TypeScript pour le build *bibliothèque* du widget.
        -   Définit `initialiserWidget()` et l'expose sur `window.LivrerJardinerWidget`.
    -   `shared/` (Optionnel): Peut contenir du code partagé (types, utilitaires, etc.).

## Fonctionnalités

### Widget
-   **Interface de Chat**: Permet aux utilisateurs de poser des questions au chatbot.
-   **Intégration API**: Se connecte à l'API backend (`https://api.livrerjardiner.fr`) pour `/chat` et `/order`.
-   **Prise de Commande**: Possibilité d'initier une commande depuis le chat.
-   **Sélection Modèle IA**: Choix entre différents modèles.
-   **Déplaçable et Pliable/Dépliable**.

### Interface d'Administration
-   (En cours) Vise à fournir une interface CRUD pour gérer les données de l'application via l'API FastAPI, en utilisant React-Admin.

## Utilisation du Widget (Intégration Web)

Pour intégrer le widget dans une page web externe :

1.  **Assurez-vous que React et ReactDOM sont disponibles** sur la page hôte. Le build du widget ne les inclut pas pour rester léger.
    ```html
    <!-- Exemple via CDN -->
    <script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js" crossorigin></script>
    ```
2.  **Inclure le bundle JavaScript UMD du widget** (généré par `npm run build:widget`) dans votre page HTML. Le fichier se trouvera dans `dist/widget/livrerjardiner-widget.umd.js`.
    ```html
    <script src="/chemin/vers/votre/dist/widget/livrerjardiner-widget.umd.js"></script>
    ```
3.  **Ajouter un conteneur** (par exemple, un `div`) avec un ID unique.
    ```html
    <div id="mon-widget-livrerjardiner"></div>
    ```
4.  **Appeler la fonction d'initialisation** globale après le chargement du script du widget :
    ```javascript
    // Attendre que le DOM soit prêt et que le script soit chargé
    document.addEventListener('DOMContentLoaded', function() {
      if (window.LivrerJardinerWidget && window.LivrerJardinerWidget.initialiser) {
        window.LivrerJardinerWidget.initialiser('mon-widget-livrerjardiner');
      } else {
        console.error("La fonction d'initialisation du widget LivrerJardiner n'est pas disponible.");
      }
    });
    ```

## Développement

-   **Lancer le serveur de développement (pour l'admin)** :
    ```bash
    npm run dev
    ```
-   **Construire le widget seul** (sortie dans `dist/widget/`) :
    ```bash
    npm run build:widget
    ```
-   **Construire l'admin seul** (sortie dans `dist/admin/`) :
    ```bash
    npm run build:admin
    ```
-   **Construire les deux** :
    ```bash
    npm run build
    ```
-   **Prévisualiser le build de l'admin** :
    ```bash
    npm run preview:admin
    ```
-   **Déployer l'admin sur GitHub Pages** (si configuré) :
    ```bash
    npm run deploy
    ```
