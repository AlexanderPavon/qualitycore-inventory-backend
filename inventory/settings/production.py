"""
Configuración para ambiente de PRODUCCIÓN.
Usa este archivo cuando despliegas en Railway, Heroku, AWS, etc.
"""
from .base import *  # noqa: F401, F403

# --- Debug mode (SIEMPRE desactivado en producción) ---
DEBUG = False

# --- Database: Usa SSL en producción ---
DATABASES['default']['OPTIONS'] = {
    'sslmode': 'require',
}

# --- Cookies: Configuración para producción (HTTPS) ---
SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True  # HTTPS obligatorio
CSRF_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True  # HTTPS obligatorio

# --- Seguridad adicional (solo producción) ---
SECURE_SSL_REDIRECT = True  # Redirige HTTP → HTTPS automáticamente
SECURE_HSTS_SECONDS = 31536000  # HSTS por 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True  # Aplica HSTS a subdominios
SECURE_HSTS_PRELOAD = True  # Permite lista HSTS precargada
X_FRAME_OPTIONS = 'DENY'  # Previene iframes (anti-clickjacking)
SECURE_CONTENT_TYPE_NOSNIFF = True  # Previene MIME sniffing

# --- Logging más estricto en producción ---
LOGGING['handlers']['console']['level'] = 'INFO'
LOGGING['loggers']['django']['level'] = 'WARNING'
LOGGING['loggers']['inventory_app']['level'] = 'INFO'

# --- Sentry Error Monitoring (solo en producción) ---
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=env('SENTRY_DSN', default=''),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
    ],
    # Porcentaje de transacciones a monitorear (0.0 a 1.0)
    traces_sample_rate=0.3,
    profiles_sample_rate=0.3,
    environment='production',
    send_default_pii=False,  # No enviar info personal
)

# --- Email: Usa servicio real en producción ---
# La configuración de EMAIL ya está en base.py usando variables de entorno

print(">>> Usando configuracion de PRODUCCION (production.py)")
