# logging_config.py
"""
Configuración de logging para el proyecto.
- Desarrollo: formato legible en texto plano
- Producción: formato JSON estructurado (compatible con CloudWatch, Datadog, ELK)
"""
import os

# Crear directorio de logs si no existe
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Detectar entorno: producción usa JSON, desarrollo usa texto plano
_IS_PRODUCTION = os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('production')

# Formateadores
_FORMATTERS = {
    'verbose': {
        'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
        'style': '{',
    },
    'simple': {
        'format': '[{levelname}] {asctime} {message}',
        'style': '{',
    },
    'audit': {
        'format': '[AUDIT] {asctime} | {message}',
        'style': '{',
    },
}

# En producción, agregar formateador JSON si python-json-logger está instalado
try:
    from pythonjsonlogger import jsonlogger  # noqa: F401
    _FORMATTERS['json'] = {
        '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
        'format': '%(asctime)s %(levelname)s %(name)s %(module)s %(process)d %(message)s',
    }
    _HAS_JSON_LOGGER = True
except ImportError:
    _HAS_JSON_LOGGER = False

# En producción con JSON disponible, usarlo; sino, usar verbose
_PROD_FORMATTER = 'json' if (_IS_PRODUCTION and _HAS_JSON_LOGGER) else 'verbose'

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': _FORMATTERS,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': _PROD_FORMATTER if _IS_PRODUCTION else 'simple',
        },
        'file_general': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'general.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': _PROD_FORMATTER,
        },
        'file_audit': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'audit.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,  # Mantener más backups para auditoría
            'formatter': _PROD_FORMATTER if _IS_PRODUCTION else 'audit',
        },
        'file_errors': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'errors.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': _PROD_FORMATTER,
        },
        'file_inventory': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'inventory.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': _PROD_FORMATTER,
        },
    },
    'loggers': {
        # Logger principal de Django
        'django': {
            'handlers': ['console', 'file_general', 'file_errors'],
            'level': 'INFO',
            'propagate': False,
        },
        # Logger de auditoría (middleware)
        'inventory_app.audit': {
            'handlers': ['file_audit', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Logger de inventario (servicio)
        'inventory_app.services': {
            'handlers': ['file_inventory', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Logger general de la app
        'inventory_app': {
            'handlers': ['console', 'file_general', 'file_errors'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file_general'],
        'level': 'INFO',
    },
}
