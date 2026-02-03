# Proceso web principal (servidor Django con Gunicorn)
web: gunicorn inventory.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120

# Worker de Celery para tareas asíncronas
worker: celery -A inventory worker --loglevel=info

# Job de migración (ejecutar manualmente en Railway antes de cada deploy)
# Este proceso NO debe estar siempre corriendo, solo ejecutarlo cuando sea necesario
release: bash migrate.sh
