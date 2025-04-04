import * as React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import { Link } from 'react-router-dom';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import Button from '@mui/material/Button';

// Page simple indiquant que l'enregistrement est à implémenter
const RegisterPage = () => (
    <Box display="flex" justifyContent="center" alignItems="center" minHeight="90vh">
        <Card sx={{ maxWidth: 450, padding: 2 }}>
             <Button 
                component={Link} 
                to="/login" 
                startIcon={<ArrowBackIcon />}
                sx={{ marginBottom: 2 }}
            >
                Retour à la connexion
            </Button>
            <CardContent>
                <Typography variant="h5" component="h1" gutterBottom align="center">
                    Création de compte
                </Typography>
                <Typography variant="body1" align="center">
                    (Le formulaire d'enregistrement sera implémenté ici.)
                </Typography>
                {/* Le futur formulaire ira ici */}
            </CardContent>
        </Card>
    </Box>
);

export default RegisterPage; 