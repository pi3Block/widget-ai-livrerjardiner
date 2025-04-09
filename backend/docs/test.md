---
description: 
globs: 
alwaysApply: false
---
## 1. Architecture et Structure du Projet

### Organisation des Fichiers
```
project/
├── src/
│   ├── module_name/
│   │   ├── router.py      # Routes FastAPI
│   │   ├── schemas.py     # Modèles Pydantic
│   │   ├── models.py      # Modèles SQLModel
│   │   ├── dependencies.py # Dépendances FastAPI
│   │   ├── config.py      # Configuration locale
│   │   ├── constants.py   # Constantes
│   │   ├── exceptions.py  # Exceptions personnalisées
│   │   ├── service.py     # Logique métier
│   │   └── utils.py       # Utilitaires
│   ├── config.py          # Configuration globale
│   ├── database.py        # Configuration DB
│   └── main.py           # Point d'entrée
├── tests/
│   └── module_name/
├── alembic/              # Migrations
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
└── docs/                 # Documentation
```

### Bonnes Pratiques de Structure
- Chaque module doit être autonome et suivre la même structure
- Utiliser `models.py` pour définir les modèles SQLModel, y compris les classes de base, les modèles de table (`table=True`), et les schémas API (ex: `UserCreate`, `UserRead`) en utilisant l'héritage pour minimiser la duplication.
- Le fichier `schemas.py` devient optionnel, à utiliser pour des schémas Pydantic très spécifiques non directement liés aux modèles de table ou si la complexité justifie une séparation.
- Les imports doivent être explicites avec le nom du module
- Éviter les imports circulaires
- Séparer clairement les responsabilités (routes, services, modèles/schémas)

## 2. Développement FastAPI

### Routes et Endpoints
- Utiliser des routers modulaires
- Documenter chaque endpoint avec des docstrings
- Valider les entrées avec Pydantic
- Gérer les erreurs de manière cohérente
- Utiliser les dépendances pour la réutilisation du code

### Validation des Données
```python
from pydantic import BaseModel, validator

class UserCreate(BaseModel):
    email: str
    password: str
    
    @validator('email')
    def validate_email(cls, v):
        if not '@' in v:
            raise ValueError('Invalid email format')
        return v
```

### Gestion des Dépendances
- Utiliser le système de dépendances de FastAPI
- Chaîner les dépendances pour une meilleure réutilisation
- Mettre en cache les dépendances quand possible
- Préférer les dépendances asynchrones

## 3. Base de Données et SQLModel

### Configuration
```python
from sqlmodel import SQLModel, create_engine
from fastapi import Depends
from typing import Generator

DATABASE_URL = "postgresql://user:password@localhost/dbname"
engine = create_engine(DATABASE_URL)

def get_session() -> Generator:
    with Session(engine) as session:
        yield session
```

### Migrations avec Alembic
- Générer des migrations avec des noms descriptifs
- Rendre les migrations réversibles
- Utiliser un template de nommage cohérent
- Tester les migrations avant déploiement

### Modèles et Schémas avec SQLModel
- **Utiliser l'héritage** : Définir une classe `Base` (ex: `UserBase(SQLModel)`) contenant les champs partagés. Faire hériter le modèle de table (ex: `User(UserBase, table=True)`) et les schémas API (ex: `UserRead(UserBase)`, `UserCreate(UserBase)`) de cette classe `Base`.
- **Séparer les préoccupations** : La classe `Base` et les schémas API sont des modèles de données (Pydantic). Seule la classe avec `table=True` est un modèle de table (SQLAlchemy).
- **Simplicité** : N'hériter que des modèles de données (`Base`), jamais des modèles de table (`table=True`). Garder la hiérarchie d'héritage aussi simple que possible.
- **Clarté** : Placer toutes ces définitions liées (Base, Table, Schémas API) dans `models.py` pour une meilleure cohérence.

```python
# Exemple dans models.py
from sqlmodel import SQLModel, Field
from typing import Optional

# 1. Modèle de base (données communes, Pydantic pur)
class ItemBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    # Ajouter d'autres champs communs ici

# 2. Modèle de table (hérite de Base, lié à la DB)
class Item(ItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id") # Exemple de clé étrangère

# 3. Schémas pour l'API (héritent de Base ou SQLModel directement)
class ItemCreate(ItemBase):
    # Peut ajouter des champs spécifiques à la création si nécessaire
    pass

class ItemRead(ItemBase):
    id: int # Toujours inclure l'ID pour la lecture
    owner_id: Optional[int] # Inclure les champs pertinents pour la lecture

class ItemUpdate(SQLModel): # Ne pas hériter forcément de Base si les champs sont différents
    name: Optional[str] = None # Rendre les champs optionnels pour la mise à jour
    description: Optional[str] = None
    # Ne pas permettre la mise à jour de l'ID ou owner_id ici typiquement
```

## 4. Tests

### Configuration des Tests
```python
from fastapi.testclient import TestClient
import pytest
from sqlmodel import Session, SQLModel, create_engine

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///./test.db")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)
```

### Bonnes Pratiques de Test
- Tester chaque endpoint
- Utiliser des fixtures pour la configuration
- Tester les cas d'erreur
- Maintenir une bonne couverture de tests
- Utiliser des données de test réalistes

## 5. Documentation

### Documentation du Code
- Utiliser des docstrings en français
- Documenter les paramètres et retours
- Inclure des exemples d'utilisation
- Maintenir une documentation à jour

### Documentation API
- Utiliser OpenAPI/Swagger
- Documenter les schémas de réponse
- Inclure des exemples de requêtes
- Maintenir une documentation interactive

## 6. Performance et Sécurité

### Optimisation
- Utiliser des index de base de données appropriés
- Implémenter du caching quand nécessaire
- Optimiser les requêtes N+1
- Utiliser des connexions de base de données poolées

### Sécurité
- Valider toutes les entrées utilisateur
- Utiliser des variables d'environnement pour les secrets
- Implémenter une authentification robuste
- Gérer les CORS correctement

## 7. Gestion des Dépendances

### Environnement Virtuel
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
```

### Requirements
- Séparer les dépendances par environnement
- Fixer les versions des dépendances
- Maintenir un fichier requirements.txt à jour
- Utiliser des outils de gestion de dépendances (poetry, pipenv)

## 8. Outils de Développement

### Linting et Formatage
```bash
# Installation
pip install black isort autoflake

# Formatage
black src tests
isort src tests
autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place src tests
```

### Pre-commit Hooks
- Configurer des hooks pour le formatage automatique
- Vérifier la qualité du code avant les commits
- Exécuter les tests avant les commits
- Vérifier les imports non utilisés
