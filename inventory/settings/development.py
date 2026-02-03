"""
Configuración para ambiente de DESARROLLO.
Usa este archivo cuando trabajas localmente.
"""
from .base import *  # noqa: F401, F403

# --- Debug mode (SIEMPRE activado en desarrollo) ---
DEBUG = True

# --- Hosts permitidos en desarrollo ---
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# --- Database: NO usa SSL en desarrollo local ---
# La configuración base ya tiene PostgreSQL configurado
# Solo necesitamos asegurar que NO use SSL
if 'OPTIONS' in DATABASES['default']:
    del DATABASES['default']['OPTIONS']

# --- Cookies: Configuración para desarrollo local (HTTP) ---
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False  # HTTP local
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = False  # HTTP local

# --- NO redirigir HTTP → HTTPS en desarrollo ---
SECURE_SSL_REDIRECT = False

# --- CORS más permisivo en desarrollo ---
CORS_ALLOW_ALL_ORIGINS = False  # Mantener seguridad
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:3000",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
]

# --- Logging más verboso en desarrollo ---
LOGGING['handlers']['console']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'INFO'
LOGGING['loggers']['inventory_app']['level'] = 'DEBUG'

# --- NO inicializar Sentry en desarrollo ---
# (El código de Sentry en base.py solo se ejecuta si DEBUG=False)

# --- Mostrar emails en consola en vez de enviarlos ---
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# --- Django Debug Toolbar (opcional - descomentar si lo usas) ---
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
# INTERNAL_IPS = ['127.0.0.1']

print(">>> Usando configuracion de DESARROLLO (development.py)")
