"""
Constantes du domaine pour le module addresses.
"""

# Messages d'erreur
ERROR_ADDRESS_NOT_FOUND = "Adresse non trouvée"
ERROR_INVALID_POSTAL_CODE = "Code postal invalide"
ERROR_INVALID_COORDINATES = "Coordonnées géographiques invalides"

# Limites et contraintes
MAX_STREET_LENGTH = 200
MAX_CITY_LENGTH = 100
MAX_POSTAL_CODE_LENGTH = 10
MAX_COUNTRY_LENGTH = 100

# Formats
POSTAL_CODE_REGEX = r"^\d{5}$"  # Format français
COORDINATES_PRECISION = 6  # Nombre de décimales pour lat/long

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100 