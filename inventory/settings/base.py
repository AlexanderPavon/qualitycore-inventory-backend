"""
Configuración base de Django - Compartida entre todos los ambientes.
"""
import os
from pathlib import Path
import environ

# --- Load environment variables ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# --- Main configuration ---
SECRET_KEY = env('SECRET_KEY')
# Lista con fallback seguro si la variable no está configurada
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# --- Installed apps ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceros
    'rest_framework',
    'corsheaders',

    # App propia
    'inventory_app.apps.InventoryAppConfig',
]

# --- Custom user model ---
AUTH_USER_MODEL = 'inventory_app.User'

# --- Custom authentication backends ---
AUTHENTICATION_BACKENDS = [
    'inventory_app.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# --- Django REST Framework configuration ---
REST_FRAMEWORK = {
    # Paginación global para todos los endpoints de lista
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,  # Número de resultados por página por defecto

    # Permitir a los clientes especificar el tamaño de página con ?page_size=100
    'PAGE_SIZE_QUERY_PARAM': 'page_size',
    'MAX_PAGE_SIZE': 50,  # Máximo permitido

    # Custom exception handler para remover prefijos de campo en errores
    'EXCEPTION_HANDLER': 'inventory_app.utils.exception_handler.custom_exception_handler',

    # Rate limiting / Throttling para prevenir abuso de APIs
    'DEFAULT_THROTTLE_CLASSES': [
        'inventory_app.throttles.BurstRateThrottle',
        'inventory_app.throttles.SustainedRateThrottle',
        'inventory_app.throttles.AnonBurstRateThrottle',
        'inventory_app.throttles.AnonSustainedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        # Usuarios autenticados (límites generosos para desarrollo/uso normal)
        'burst': '300/min',           # 300 requests por minuto (ráfagas cortas)
        'sustained': '5000/hour',     # 5000 requests por hora (uso sostenido)

        # Usuarios anónimos (más restrictivo)
        'anon_burst': '100/min',      # 100 requests por minuto
        'anon_sustained': '500/hour',  # 500 requests por hora

        # Endpoints críticos de autenticación
        'login': '10/min',            # Máximo 10 intentos de login por minuto (previene brute force)
        'password_reset': '5/hour',   # Máximo 5 solicitudes de reset por hora
        'password_change': '10/hour', # Máximo 10 cambios de contraseña por hora

        # Operaciones de escritura
        'write': '100/min',           # 100 operaciones de escritura por minuto
    },
}

# --- Middleware ---
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'inventory_app.middleware.AuditMiddleware',  # Audit trail middleware
]

# --- Root URLs and WSGI ---
ROOT_URLCONF = 'inventory.urls'
WSGI_APPLICATION = 'inventory.wsgi.application'

# --- Templates ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# --- Database configuration (PostgreSQL) ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
        'CONN_MAX_AGE': 60,  # DB connection pooling
    }
}

# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {'NAME': 'inventory_app.validators.password_validators.ComplexPasswordValidator'},
]

# --- Email configuration (for password recovery) ---
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env('EMAIL_PORT')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS')
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')

# --- Frontend URL (for password reset emails) ---
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:3000')

# --- Internationalization ---
LANGUAGE_CODE = 'es-ec'
TIME_ZONE = 'America/Guayaquil'
USE_I18N = True
USE_TZ = True

# --- Static and media files ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- Primary key field type ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- CORS (for React frontend) ---
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        "http://localhost:3000",
        "https://qualitycore-inventory-frontend-production.up.railway.app",
    ]
)

# --- CSRF (for secure POST requests) ---
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=[
        "http://localhost:3000",
        "https://qualitycore-inventory-frontend-production.up.railway.app",
    ]
)

# --- Permitir cookies (credentials) entre dominios
CORS_ALLOW_CREDENTIALS = True

# --- Security / Proxy ---
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# --- Cloudinary (Opcional - activar USE_CLOUDINARY=true del .env) ---
USE_CLOUDINARY = env.bool("USE_CLOUDINARY", default=False)

if USE_CLOUDINARY:
    import cloudinary  # noqa: E402

    INSTALLED_APPS += ["cloudinary", "cloudinary_storage"]

    # Nueva sintaxis STORAGES para Django 5.2+
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

    # Configuración de Cloudinary
    cloudinary.config(
        cloud_name=env("CLOUDINARY_CLOUD_NAME"),
        api_key=env("CLOUDINARY_API_KEY"),
        api_secret=env("CLOUDINARY_API_SECRET"),
        secure=True
    )

# --- Logging configuration ---
from inventory_app.logging_config import LOGGING_CONFIG as LOGGING_DICT

LOGGING = LOGGING_DICT

# --- Celery configuration ---
REDIS_URL = env('REDIS_URL', default=env('CELERY_BROKER_URL', default='redis://localhost:6379/0'))
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Configuración de tareas
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos máximo por tarea
CELERY_RESULT_EXPIRES = 3600  # Los resultados expiran después de 1 hora
