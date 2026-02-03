# celery.py
"""
Configuración de Celery para tareas asíncronas.
Usado principalmente para generación de PDFs y tareas pesadas.
"""
import os
from celery import Celery

# Establecer el módulo de configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory.settings')

# Crear la aplicación Celery
app = Celery('inventory')

# Cargar la configuración desde Django settings usando el namespace 'CELERY'
# Esto significa que todas las configuraciones de Celery en settings.py deben empezar con CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubrir tareas en todos los archivos tasks.py de las apps instaladas
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tarea de prueba para verificar que Celery funciona correctamente."""
    print(f'Request: {self.request!r}')
