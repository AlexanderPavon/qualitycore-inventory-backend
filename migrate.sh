#!/bin/bash
# Script de migración para ejecutar en deploy
# Este script debe ejecutarse UNA VEZ antes de arrancar las instancias del servidor

set -e  # Detener si hay errores

echo "🔄 Iniciando proceso de migración..."

# Ejecutar migraciones
echo "📦 Ejecutando migraciones de base de datos..."
python manage.py migrate --noinput

# Crear usuarios iniciales si no existen
echo "👥 Verificando usuarios iniciales..."
python manage.py create_initial_users

# Recolectar archivos estáticos (opcional, útil para producción)
echo "📁 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear || true

echo "✅ Migración completada exitosamente"
