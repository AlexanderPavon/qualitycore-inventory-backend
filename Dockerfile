# ✅ Imagen base de Python
FROM python:3.11-slim

# ✅ Establecer directorio de trabajo
WORKDIR /app

# ✅ Copiar el archivo de requerimientos
COPY requirements.txt .

# ✅ Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Copiar el resto del proyecto
COPY . .

# ✅ Variables de entorno para Django
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=inventory.settings

# ✅ Exponer el puerto
EXPOSE 8000

# ✅ Comando para correr el servidor en producción con Gunicorn
CMD ["gunicorn", "inventario.wsgi:application", "--bind", "0.0.0.0:8000"]
