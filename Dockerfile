# ✅ Imagen base de Python
FROM python:3.11-slim

# ✅ Directorio de trabajo
WORKDIR /app

# ✅ Optimizaciones de Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ✅ Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Copiar el proyecto
COPY . .

# ✅ Ajustes Django
ENV DJANGO_SETTINGS_MODULE=inventory.settings

# ✅ Exponer (informativo)
EXPOSE 8000

# ✅ Migrar y luego correr Gunicorn usando el puerto de Railway
CMD ["bash","-c","python manage.py migrate && gunicorn inventory.wsgi:application --bind 0.0.0.0:$PORT"]
