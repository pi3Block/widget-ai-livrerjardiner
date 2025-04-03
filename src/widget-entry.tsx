import React from 'react';
import ReactDOM from 'react-dom/client';
import Widget from './Widget'; // Votre composant principal

// Fonction pour initialiser le widget
function initialiserWidget(containerId) {
  let container = document.getElementById(containerId);

  // Si le conteneur n'existe pas, on peut le créer dynamiquement
  if (!container) {
    console.warn(`Conteneur #${containerId} non trouvé. Création dynamique.`);
    container = document.createElement('div');
    container.id = containerId;
    // Vous pourriez vouloir l'ajouter à un endroit spécifique du body
    // ou demander à l'utilisateur de le placer manuellement.
    // Pour l'instant, ajoutons-le au body.
    document.body.appendChild(container);
  }

  const root = ReactDOM.createRoot(container);
  root.render(
    <React.StrictMode>
      <Widget />
    </React.StrictMode>
  );
}

// Exposer la fonction globalement pour qu'elle soit appelable depuis l'extérieur
window.MonWidgetReact = {
  initialiser: initialiserWidget
};

// Optionnel: Auto-initialisation si un élément spécifique existe déjà
// const autoMountElement = document.getElementById('mon-widget-react-auto');
// if (autoMountElement) {
//   initialiserWidget('mon-widget-react-auto');
// }

export default initialiserWidget; // Export au cas où (pour UMD)
