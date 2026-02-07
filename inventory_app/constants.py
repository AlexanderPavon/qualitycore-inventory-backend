# constants.py
"""
Constantes del sistema para evitar magic strings y valores duplicados.
Centraliza valores que se usan en múltiples lugares.
"""

class MovementType:
    """Tipos de movimiento de inventario"""
    INPUT = 'input'
    OUTPUT = 'output'

    CHOICES = [
        (INPUT, 'Entrada'),
        (OUTPUT, 'Salida'),
    ]


class UserRole:
    """Roles de usuario del sistema"""
    SUPER_ADMIN = 'SuperAdmin'
    ADMINISTRATOR = 'Administrator'
    USER = 'User'

    CHOICES = [
        (SUPER_ADMIN, 'SuperAdmin'),
        (ADMINISTRATOR, 'Administrator'),
        (USER, 'User'),
    ]


class ProductStatus:
    """Estados de productos"""
    AVAILABLE = 'Disponible'
    OUT_OF_STOCK = 'Agotado'
    LOW_STOCK = 'Stock Bajo'

    CHOICES = [
        (AVAILABLE, 'Disponible'),
        (OUT_OF_STOCK, 'Agotado'),
        (LOW_STOCK, 'Stock Bajo'),
    ]


class ValidationMessages:
    """Mensajes de validación estandarizados"""

    # Teléfono
    PHONE_INVALID_FORMAT = 'El teléfono debe tener exactamente 10 dígitos.'
    PHONE_REGEX = r'^\d{10}$'

    # Email
    EMAIL_INVALID = 'El correo electrónico no es válido.'

    # Documento (Cédula/RUC)
    DOCUMENT_INVALID_FORMAT = 'La cédula o RUC debe tener entre 10 y 13 dígitos numéricos.'
    DOCUMENT_REGEX = r'^\d{10,13}$'

    # Precio
    PRICE_NEGATIVE = 'El precio no puede ser negativo.'

    # Cantidad
    QUANTITY_INVALID = 'La cantidad debe ser mayor a 0.'
    QUANTITY_MIN_ONE = 'La cantidad debe ser al menos 1.'

    # Stock
    STOCK_INSUFFICIENT = 'Stock insuficiente. Disponible: {available}, solicitado: {requested}.'

    # Cotizaciones
    QUOTATION_MIN_PRODUCTS = 'Debe agregar al menos un producto a la cotización.'
    QUOTATION_PRODUCT_QUANTITY_INVALID = 'Producto {index}: La cantidad debe ser mayor a 0.'
    QUOTATION_PRODUCT_PRICE_INVALID = 'Producto {index}: El precio unitario no puede ser negativo.'

    # Movimientos
    MOVEMENT_CUSTOMER_REQUIRED = 'El cliente es requerido para movimientos de salida.'


class BusinessRules:
    """Reglas de negocio centralizadas"""

    # IVA Ecuador
    TAX_RATE = 0.15  # 15%

    # Validaciones
    MIN_PHONE_LENGTH = 10
    MAX_PHONE_LENGTH = 10
    MIN_DOCUMENT_LENGTH = 10
    MAX_DOCUMENT_LENGTH = 13
    MIN_PASSWORD_LENGTH = 8

    # Límites
    MAX_PRODUCT_PRICE = 9999999.99
    MAX_QUANTITY = 99999

    # Paginación
    DEFAULT_PAGE_SIZE = 20
    PAGE_SIZE_OPTIONS = [10, 20, 50, 100]


class Timeouts:
    """Timeouts en milisegundos para el frontend"""
    TOAST_DEFAULT = 5000
    TOAST_SHORT = 3000
    TOAST_LONG = 8000
    MESSAGE_DISPLAY = 4000
    REDIRECT_DELAY = 2000
    POLLING_INTERVAL = 2000
    CLOCK_INTERVAL = 1000


class ImageConfig:
    """Configuración de imágenes"""
    MAX_SIZE_MB = 2
    MAX_SIZE_BYTES = 2 * 1024 * 1024
    MIN_WIDTH = 300
    MIN_HEIGHT = 300
    MAX_WIDTH = 2000
    MAX_HEIGHT = 2000
    ALLOWED_TYPES = ['image/jpeg', 'image/png']
    ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png']
