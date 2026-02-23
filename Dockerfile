# Imagen base de Python
FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Optimizaciones de Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Crear usuario no-root para seguridad
RUN addgroup --system app && adduser --system --ingroup app app

# Copiar el proyecto
COPY . .

# Ajustes Django
ENV DJANGO_SETTINGS_MODULE=inventory.settings

# Exponer (informativo)
EXPOSE 8000

# Copiar script de migración y darle permisos
COPY migrate.sh .
RUN chmod +x migrate.sh

# Crear directorios que la app necesita escribir y asignar permisos
RUN mkdir -p /app/logs /app/media && chown -R app:app /app/logs /app/media

# Ejecutar como usuario no-root
USER app

# Solo correr Gunicorn (las migraciones se ejecutan en un job separado)
# Nota: Railway usa $PORT dinámico, pero el Procfile sobrescribe este CMD
CMD ["sh", "-c", "gunicorn inventory.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --timeout 120"]
