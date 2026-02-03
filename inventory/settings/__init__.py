"""
Inicialización del paquete de configuración.

Determina automáticamente qué archivo de settings usar basándose en la variable
de entorno DJANGO_ENV.

Valores posibles:
- DJANGO_ENV=production → usa production.py
- DJANGO_ENV=development → usa development.py
- Sin DJANGO_ENV → usa development.py por defecto
"""
import os

# Obtener entorno desde variable de entorno
django_env = os.environ.get('DJANGO_ENV', 'development').lower()

# Importar configuración según ambiente
if django_env == 'production':
    from .production import *  # noqa: F401, F403
elif django_env == 'development':
    from .development import *  # noqa: F401, F403
else:
    # Por defecto usar development si no se reconoce el ambiente
    print(f"⚠️  Ambiente '{django_env}' no reconocido. Usando 'development' por defecto.")
    from .development import *  # noqa: F401, F403
