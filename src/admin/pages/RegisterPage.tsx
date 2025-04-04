import * as React from 'react';
import { useState } from 'react';
import { Card, CardContent, Typography, Box, Button } from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import {
    SimpleForm,
    TextInput,
    PasswordInput,
    required,
    email,
    useNotify,
    SaveButton,
    Toolbar,
} from 'react-admin';

// URL de l'API pour l'enregistrement
const API_URL = 'https://api.livrerjardiner.fr'; 

// Validateur pour vérifier que les mots de passe correspondent
const validatePasswordMatch = (value: string, allValues: any) => {
    if (value !== allValues.password) {
        return 'Les mots de passe ne correspondent pas';
    }
    return undefined;
};

// Barre d'outils personnalisée pour le formulaire d'enregistrement
const RegisterToolbar = ({ loading, ...props }: any) => (
    <Toolbar {...props} sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <SaveButton label="Créer le compte" icon={<></>} disabled={loading} />
    </Toolbar>
);

const RegisterPage = () => {
    const [loading, setLoading] = useState(false);
    const notify = useNotify();
    const navigate = useNavigate();

    const handleSubmit = async (values: any) => {
        setLoading(true);
        // Supprimer la confirmation du mot de passe avant l'envoi
        const { confirm_password, ...userData } = values; 
        
        try {
            const response = await fetch(`${API_URL}/users/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userData), // Envoyer name, email, password
            });

            if (!response.ok) {
                // Essayer de lire le message d'erreur du backend
                let errorMessage = `Erreur ${response.status}: ${response.statusText}`;
                try {
                    const errorBody = await response.json();
                    errorMessage = errorBody.detail || errorMessage;
                } catch (e) {
                    // Ignorer si le corps n'est pas JSON
                }
                 // Gérer spécifiquement le cas 409 (Email existe déjà)
                if (response.status === 409) {
                    errorMessage = "Un compte avec cet email existe déjà.";
                } else if (response.status === 422) {
                    errorMessage = "Données invalides. Vérifiez les champs."; // Ou utiliser errorBody.detail si plus précis
                }
                
                notify(errorMessage, { type: 'warning' });
                setLoading(false);
                return; // Arrêter ici en cas d'erreur
            }

            // Succès de la création
            notify('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', { type: 'success' });
            setLoading(false);
            // Rediriger vers la page de connexion après un court délai
            setTimeout(() => navigate('/login'), 1500); 

        } catch (error) {
            console.error("Erreur lors de la création du compte:", error);
            notify('Erreur réseau ou serveur lors de la création du compte.', { type: 'error' });
            setLoading(false);
        }
    };

    return (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="90vh">
            <Card sx={{ minWidth: 350, maxWidth: 450, padding: 2 }}>
                 <Button 
                    component={Link} 
                    to="/login" 
                    startIcon={<ArrowBackIcon />}
                    sx={{ marginBottom: 2 }}
                    disabled={loading}
                >
                    Retour à la connexion
                </Button>
                <CardContent>
                    <Typography variant="h5" component="h1" gutterBottom align="center">
                        Création de compte
                    </Typography>
                    
                    <SimpleForm
                        onSubmit={handleSubmit}
                        mode="onChange"
                        toolbar={<RegisterToolbar loading={loading} />}
                    >
                        <TextInput 
                            source="name" 
                            label="Nom complet" 
                            validate={required()} 
                            fullWidth 
                            disabled={loading}
                        />
                        <TextInput 
                            source="email" 
                            label="Email" 
                            type="email" 
                            validate={[required(), email()]} 
                            fullWidth 
                            disabled={loading}
                        />
                        <PasswordInput 
                            source="password" 
                            label="Mot de passe" 
                            validate={required()} 
                            fullWidth 
                            disabled={loading}
                        />
                        <PasswordInput 
                            source="confirm_password" 
                            label="Confirmer le mot de passe" 
                            validate={[required(), validatePasswordMatch]} 
                            fullWidth 
                            disabled={loading}
                        />
                    </SimpleForm>
                </CardContent>
            </Card>
        </Box>
    );
};

export default RegisterPage; 