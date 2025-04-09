# Module Orders

Ce module gère les commandes et les lignes de commande dans l'application.

## Modèles et Schémas

Le module utilise SQLModel pour définir à la fois les modèles de base de données et les schémas API, réduisant ainsi la duplication de code.

### Modèles de base de données

- `Order` : Représente une commande
- `OrderItem` : Représente une ligne de commande

### Schémas API

- `OrderCreate` : Schéma pour la création d'une commande
- `OrderResponse` : Schéma pour la réponse d'une commande
- `OrderUpdate` : Schéma pour la mise à jour d'une commande
- `OrderItemCreate` : Schéma pour la création d'une ligne de commande
- `OrderItemResponse` : Schéma pour la réponse d'une ligne de commande
- `PaginatedOrderResponse` : Schéma pour la réponse paginée d'une liste de commandes

## Utilisation

Pour utiliser ce module, importez les classes nécessaires depuis `src.orders` :

```python
from src.orders import Order, OrderCreate, OrderResponse
```

## Flux de travail

1. Le client envoie une requête de création de commande avec `OrderCreate`
2. Le service valide les données, vérifie le stock, etc.
3. La commande est créée en base de données
4. Le service retourne une réponse avec `OrderResponse` 