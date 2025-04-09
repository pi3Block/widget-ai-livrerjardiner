"""
Exceptions personnalisées pour le module de gestion des utilisateurs.
"""

class UserError(Exception):
    """Classe de base pour les exceptions liées aux utilisateurs."""
    pass

class UserNotFoundError(UserError):
    """Levée lorsque l'utilisateur n'est pas trouvé."""
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"Utilisateur {user_id} non trouvé")

class UserAlreadyExistsError(UserError):
    """Levée lorsqu'un utilisateur avec cet email existe déjà."""
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Un utilisateur avec l'email {email} existe déjà")

class InvalidCredentialsError(UserError):
    """Levée lorsque les identifiants sont invalides."""
    def __init__(self, message: str = "Identifiants invalides"):
        super().__init__(message)

class AccountDisabledError(UserError):
    """Levée lorsque le compte est désactivé."""
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"Le compte de l'utilisateur {user_id} est désactivé")

class InvalidRoleError(UserError):
    """Levée lorsque le rôle est invalide."""
    def __init__(self, role: str):
        self.role = role
        super().__init__(f"Rôle invalide: {role}")

class PasswordValidationError(UserError):
    """Levée lorsque la validation du mot de passe échoue."""
    def __init__(self, message: str):
        super().__init__(f"Erreur de validation du mot de passe: {message}")

class TokenError(UserError):
    """Levée lorsqu'il y a un problème avec le token."""
    def __init__(self, message: str):
        super().__init__(f"Erreur de token: {message}") 