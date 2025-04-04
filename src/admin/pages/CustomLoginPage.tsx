import * as React from 'react';
import { Login, LoginForm } from 'react-admin';
import { Box, Button, Divider, TextField } from '@mui/material';
import { Link } from 'react-router-dom';

// Composant LoginForm personnalisé si nécessaire (pour l'instant, utilise le standard)
// const CustomLoginForm = props => (
//   <Box component="form" onSubmit={props.onSubmit}>
//     <LoginForm {...props} />
//   </Box>
// );

// Créer une version personnalisée de l'input pour le username avec le label "Email"
const EmailInput = (props: any) => (
    <TextField
        {...props}
        label="Email"
        variant="filled"
        margin="normal"
        fullWidth
    />
);

// Page de connexion personnalisée avec bouton "Créer un compte"
const CustomLoginPage = (props: any) => (
    <Login {...props}>
        <Box sx={{ width: '100%', maxWidth: 400, margin: 'auto' }}>
            {/* Utilise le formulaire de connexion avec l'input Email personnalisé */}
            <LoginForm 
                {...props} 
                usernameInput={<EmailInput source="username" />} 
            /> 
            
            <Divider sx={{ my: 2 }} />
            
            <Box sx={{ textAlign: 'center' }}>
                <Button 
                    component={Link} 
                    to="/register"
                    variant="text"
                    color="primary"
                >
                    Créer un compte
                </Button>
            </Box>
        </Box>
    </Login>
);

export default CustomLoginPage; 