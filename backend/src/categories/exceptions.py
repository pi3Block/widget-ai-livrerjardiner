"""Exceptions personnalisées pour le module categories."""

from fastapi import HTTPException
from .constants import (
    ERROR_CATEGORY_NOT_FOUND,
    ERROR_CATEGORY_NAME_EXISTS,
    ERROR_INVALID_PARENT,
    ERROR_CODE_NOT_FOUND,
    ERROR_CODE_CONFLICT,
    ERROR_CODE_BAD_REQUEST
)

class CategoryNotFoundException(Exception):
    """Exception levée lorsqu'une catégorie n'est pas trouvée."""
    def __init__(self, category_id: int = None, message: str = "Catégorie non trouvée"):
        self.category_id = category_id
        self.message = f"{message}{f' (ID: {category_id})' if category_id else ''}."
        super().__init__(self.message)

class DuplicateCategoryNameException(Exception):
    """Exception levée lorsqu'une catégorie avec le même nom existe déjà."""
    def __init__(self, name: str):
        self.name = name
        self.message = f"Une catégorie avec le nom '{name}' existe déjà."
        super().__init__(self.message)

class CategoryUpdateFailedException(Exception):
    """Exception levée lors d'un échec de la mise à jour de la catégorie."""
    def __init__(self, category_id: int, message: str = "Échec de la mise à jour de la catégorie"):
        self.category_id = category_id
        self.message = f"{message} (ID: {category_id})."
        super().__init__(self.message)

class CategoryCreationFailedException(Exception):
    """Exception levée lors d'un échec de la création de la catégorie."""
    def __init__(self, message: str = "Échec de la création de la catégorie"):
        self.message = message
        super().__init__(self.message)

class InvalidCategoryOperationException(Exception):
    """Exception pour des opérations invalides sur les catégories."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class CategoryNotFound(HTTPException):
    """Exception levée quand une catégorie n'est pas trouvée."""
    def __init__(self):
        super().__init__(
            status_code=ERROR_CODE_NOT_FOUND,
            detail=ERROR_CATEGORY_NOT_FOUND
        )

class CategoryNameExists(HTTPException):
    """Exception levée quand une catégorie avec le même nom existe déjà."""
    def __init__(self):
        super().__init__(
            status_code=ERROR_CODE_CONFLICT,
            detail=ERROR_CATEGORY_NAME_EXISTS
        )

class InvalidParentCategory(HTTPException):
    """Exception levée quand la catégorie parente est invalide."""
    def __init__(self):
        super().__init__(
            status_code=ERROR_CODE_BAD_REQUEST,
            detail=ERROR_INVALID_PARENT
        ) 