# Templates de Facture

Ce dossier contient les fichiers nécessaires pour générer des factures au format PDF.

## Structure des fichiers

- `invoice.html` : Template HTML de la facture
- `invoice.css` : Styles CSS pour la mise en forme de la facture

## Variables disponibles

Le template utilise les variables suivantes qui doivent être fournies lors de la génération du PDF :

### Informations de l'entreprise
- `company.name` : Nom de l'entreprise
- `company.address` : Adresse de l'entreprise
- `company.phone` : Numéro de téléphone
- `company.email` : Adresse email
- `company.siret` : Numéro SIRET

### Informations de la facture
- `invoice_number` : Numéro de la facture
- `invoice_date` : Date de la facture

### Informations du client
- `client.name` : Nom du client
- `client.address` : Adresse du client
- `client.phone` : Numéro de téléphone
- `client.email` : Adresse email

### Articles
- `items` : Tableau des articles avec les propriétés suivantes pour chaque article :
  - `description` : Description de l'article
  - `quantity` : Quantité
  - `unit_price` : Prix unitaire
  - `total` : Total pour cet article

### Totaux
- `total_ht` : Total hors taxes
- `tva_rate` : Taux de TVA
- `total_tva` : Montant de la TVA
- `total_ttc` : Total toutes taxes comprises

## Utilisation

Pour générer une facture, il faut :
1. Préparer un objet contenant toutes les variables nécessaires
2. Utiliser un moteur de template (comme Handlebars) pour remplir le template HTML
3. Convertir le HTML en PDF en utilisant une bibliothèque comme Puppeteer

## Personnalisation

Pour modifier l'apparence de la facture :
1. Modifier le fichier `invoice.css` pour changer les styles
2. Modifier le fichier `invoice.html` pour changer la structure
3. S'assurer que les variables utilisées dans le HTML correspondent aux données fournies 