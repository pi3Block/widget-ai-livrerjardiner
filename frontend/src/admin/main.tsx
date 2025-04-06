import React from 'react';
import ReactDOM from 'react-dom/client';
// Importer fetchUtils ET le type Options depuis react-admin
// Ajouter CustomRoutes et Route
import { Admin, Resource, ListGuesser, EditGuesser, fetchUtils, Options, CustomRoutes } from 'react-admin'; 
import { Route } from 'react-router-dom'; // Importer Route pour CustomRoutes
import simpleRestProvider from 'ra-data-simple-rest';

// Importer les composants CRUD complets pour Product (corriger le chemin)
import { ProductList, ProductEdit, ProductCreate } from './components/products'; 
// Importer les composants CRUD pour Categories
import { CategoryList, CategoryEdit, CategoryCreate } from './components/categories';

// Importer l'authProvider
import { authProvider } from './authProvider';

// Importer la page de connexion personnalisée et la page d'enregistrement
import CustomLoginPage from './pages/CustomLoginPage';
import RegisterPage from './pages/RegisterPage';

const API_URL = 'https://api.livrerjardiner.fr'; 

// Créer un httpClient personnalisé qui ajoute le token
// Utiliser le type Options importé de react-admin
const httpClient = (url: string, options: Options = {}) => {
    // Créer un nouvel objet Headers à partir des headers existants (ou vide)
    const customHeaders = (options.headers || new Headers({
        Accept: 'application/json',
    })) as Headers;
    
    const token = localStorage.getItem('access_token');
    // Ajouter l'en-tête Authorization si le token existe
    if (token) {
        customHeaders.set('Authorization', `Bearer ${token}`);
    }
    
    // Mettre à jour les headers dans les options
    options.headers = customHeaders;
    
    // Appeler la fonction fetchJson originale avec les options mises à jour
    return fetchUtils.fetchJson(url, options);
};

// Créer le dataProvider en utilisant le httpClient personnalisé
const dataProvider = simpleRestProvider(API_URL, httpClient);

// Composant principal de l'application Admin
const AppAdmin = () => (
  // Utiliser loginPage prop pour spécifier la page de connexion personnalisée
  <Admin 
    dataProvider={dataProvider} 
    authProvider={authProvider} 
    loginPage={CustomLoginPage} // Utiliser la page personnalisée
  >
    {/* Ressource Products avec List, Edit, Create */}
    <Resource 
      name="products" 
      list={ProductList} 
      edit={ProductEdit} 
      create={ProductCreate} 
      // show={ProductShow} // Ajouter plus tard si vous créez une vue de détail
      options={{ label: 'Produits' }} // Nom affiché dans le menu
    />
    
    {/* Ressource Categories */}
    <Resource 
      name="categories" 
      list={CategoryList} 
      edit={CategoryEdit}
      create={CategoryCreate}
      options={{ label: 'Catégories' }} 
      recordRepresentation="name" // Affiche le nom dans certains contextes (ex: titre édition)
    />
    
    {/* <Resource name="users" list={ListGuesser} options={{ label: \'Utilisateurs\' }} /> */}
    {/* <Resource name="orders" list={ListGuesser} options={{ label: \'Commandes\' }} /> */}

    {/* Ajouter la route personnalisée pour l'enregistrement */}
    <CustomRoutes>
      <Route path="/register" element={<RegisterPage />} />
    </CustomRoutes>
  </Admin>
);

// Point de montage React
const container = document.getElementById('root');

if (container) {
  const root = ReactDOM.createRoot(container);
  root.render(
    // <React.StrictMode> // Garder commenté pour l'instant
      <AppAdmin />
    // </React.StrictMode>
  );
} else {
  console.error("Élément racine introuvable. Assurez-vous qu'un élément avec l'ID 'root' existe dans index.html.");
}
