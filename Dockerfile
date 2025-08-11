# # ✅ Imagen base de Python
# FROM python:3.11-slim

# # ✅ Establecer directorio de trabajo
# WORKDIR /app

# # ✅ Copiar el archivo de requerimientos
# COPY requirements.txt .

# # ✅ Instalar dependencias
# RUN pip install --no-cache-dir -r requirements.txt

# # ✅ Copiar el resto del proyecto
# COPY . .

# # ✅ Variables de entorno para Django
# ENV PYTHONUNBUFFERED=1
# ENV DJANGO_SETTINGS_MODULE=inventory.settings

# # ✅ Exponer el puerto
# EXPOSE 8000

# # ✅ Comando para correr el servidor en producción con Gunicorn
# #CMD ["gunicorn", "inventory.wsgi:application", "--bind", "0.0.0.0:8000"]

# # ✅ Comando para migrar y luego correr Gunicorn en el puerto de Railway
# CMD ["bash","-c","python manage.py migrate && gunicorn inventory.wsgi:application --bind 0.0.0.0:$PORT"]


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
