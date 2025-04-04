import { AuthProvider } from 'react-admin';

// URL de base de votre API
const API_URL = 'https://api.livrerjardiner.fr'; 

export const authProvider: AuthProvider = {
    // Méthode appelée lors du clic sur le bouton de connexion
    login: async ({ username, password }) => {
        // /auth/token attend des données 'x-www-form-urlencoded'
        // Utiliser URLSearchParams pour construire le corps
        const formData = new URLSearchParams();
        formData.append('username', username); // FastAPI OAuth2PasswordRequestForm attend 'username'
        formData.append('password', password);

        const request = new Request(`${API_URL}/auth/token`, {
            method: 'POST',
            body: formData, // Envoyer l'objet URLSearchParams directement
            headers: new Headers({ 'Content-Type': 'application/x-www-form-urlencoded' }), // Spécifier le bon Content-Type
        });

        try {
            const response = await fetch(request);
            if (response.status < 200 || response.status >= 300) {
                throw new Error(response.statusText);
            }
            const auth = await response.json();
            // Stocker le token dans localStorage
            localStorage.setItem('access_token', auth.access_token);
            // React-admin attend que cette méthode resolve pour confirmer la connexion
            return Promise.resolve(); 
        } catch (error) {
            // Gérer les erreurs de connexion (ex: mauvais identifiants)
            console.error("Erreur de connexion:", error);
            // Améliorer le message d'erreur
            throw new Error('Échec de la connexion: Vérifiez votre email et mot de passe.');
        }
    },

    // Méthode appelée lors du clic sur le bouton de déconnexion
    logout: () => {
        localStorage.removeItem('access_token');
        // TODO: Potentiellement appeler un endpoint /logout sur le backend s'il existe
        return Promise.resolve();
    },

    // Méthode appelée à chaque navigation pour vérifier si l'utilisateur est connecté
    checkAuth: () => {
        // Vérifie simplement si le token existe
        return localStorage.getItem('access_token') 
            ? Promise.resolve() 
            : Promise.reject(); // Redirige vers la page de login si pas de token
    },

    // Méthode appelée si une requête API échoue
    checkError: (error) => {
        const status = error.status;
        if (status === 401 || status === 403) {
            // Si l'API retourne 401 (Non autorisé) ou 403 (Interdit)
            localStorage.removeItem('access_token');
            // Rejeter la promesse force la déconnexion et redirection vers login
            return Promise.reject(); 
        }
        // Ne pas gérer les autres erreurs ici (laisser react-admin/dataProvider les gérer)
        return Promise.resolve();
    },

    // Méthode pour obtenir les infos de l'utilisateur connecté
    getIdentity: async () => {
        const token = localStorage.getItem('access_token');
        if (!token) {
            return Promise.reject();
        }

        const request = new Request(`${API_URL}/users/me`, {
            method: 'GET',
            headers: new Headers({ 'Authorization': `Bearer ${token}` }),
        });

        try {
            const response = await fetch(request);
            if (response.status < 200 || response.status >= 300) {
                throw new Error(response.statusText);
            }
            const identity = await response.json();
            // React-admin attend un objet avec au moins 'id', et optionnellement 'fullName', 'avatar'
            return Promise.resolve({
                id: identity.id,
                fullName: identity.name, // Supposant que votre modèle User a un champ 'name'
                // avatar: identity.profile_picture_url, // Si vous avez une URL d'avatar
            });
        } catch (error) {
             // Si /users/me échoue (token invalide?), considérer comme déconnecté
             console.error("Erreur getIdentity:", error);
             localStorage.removeItem('access_token');
             return Promise.reject();
        }
    },

    // Méthode pour obtenir les permissions/rôles (simplifié pour l'instant)
    getPermissions: () => {
        // Pour l'instant, on suppose que si l'utilisateur est connecté, il a accès
        // Plus tard, on pourrait retourner des rôles ('admin', 'editor') basé sur getIdentity
        return Promise.resolve(); // Résoudre avec undefined ou un rôle/permission simple
    },
}; 