# Guía de Despliegue en Railway con Celery y Redis

## 1. Configurar Redis en Railway

1. En tu proyecto de Railway, haz click en **"New"** → **"Database"** → **"Add Redis"**
2. Railway creará automáticamente la variable de entorno `REDIS_URL`
3. Esta variable será usada automáticamente por Django y Celery

## 2. Crear dos servicios en Railway

Railway necesita **DOS servicios separados** en el mismo proyecto:

### Servicio 1: Web (Django)
- **Nombre**: `qualitycore-backend-web`
- **Start Command**: `gunicorn inventory.wsgi --bind 0.0.0.0:$PORT`
- **Variables de entorno**: (ver sección 3)

### Servicio 2: Worker (Celery)
- **Nombre**: `qualitycore-backend-worker`
- **Start Command**: `celery -A inventory worker --loglevel=info`
- **Variables de entorno**: Las mismas que el servicio web

## 3. Variables de entorno en Railway

Configura estas variables en **AMBOS servicios** (Web y Worker):

```bash
# Django Core
SECRET_KEY=tu_clave_secreta_segura_aqui
DEBUG=False
ALLOWED_HOSTS=.up.railway.app,tu-dominio.com

# Database (PostgreSQL - Railway lo proporciona automáticamente)
# DATABASE_URL será provisto automáticamente por Railway si agregaste PostgreSQL

# O configura manualmente:
DB_HOST=tu-host-postgres.railway.app
DB_NAME=railway
DB_USER=postgres
DB_PASSWORD=tu-password
DB_PORT=5432

# Cloudinary
CLOUDINARY_API_KEY=469118624889779
CLOUDINARY_API_SECRET=bfr2qtGBYpi9WdkBGnuk5Nx5z3c
CLOUDINARY_CLOUD_NAME=ddzz6jt4h
USE_CLOUDINARY=true

# Email
DEFAULT_FROM_EMAIL=qualitycoreservice@gmail.com
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_PASSWORD=qujs nnhw aykg vfhj
EMAIL_HOST_USER=qualitycoreservice@gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True

# Frontend URL (ajusta según tu dominio de producción)
FRONTEND_URL=https://tu-frontend.up.railway.app

# CORS y CSRF
CORS_ALLOWED_ORIGINS=https://tu-frontend.up.railway.app
CSRF_TRUSTED_ORIGINS=https://tu-backend.up.railway.app,https://tu-frontend.up.railway.app

# Redis (Railway lo proporciona automáticamente)
# REDIS_URL será provisto automáticamente cuando agregues Redis
```

## 4. Configuración en Railway (paso a paso)

### A. Crear el proyecto base
1. Conecta tu repositorio de GitHub a Railway
2. Railway detectará automáticamente que es un proyecto Django

### B. Agregar PostgreSQL
1. Click en **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway creará `DATABASE_URL` automáticamente

### C. Agregar Redis
1. Click en **"New"** → **"Database"** → **"Add Redis"**
2. Railway creará `REDIS_URL` automáticamente

### D. Crear servicio Web
1. En el servicio principal (Django):
   - Ve a **Settings** → **Deploy**
   - **Start Command**: `gunicorn inventory.wsgi --bind 0.0.0.0:$PORT`
   - Configura todas las variables de entorno listadas arriba

### E. Crear servicio Worker (Celery)
1. Click en **"New"** → **"Empty Service"**
2. Conecta el mismo repositorio de GitHub
3. Ve a **Settings** → **Deploy**
   - **Start Command**: `celery -A inventory worker --loglevel=info`
4. Configura las **mismas variables de entorno** que el servicio Web
5. **IMPORTANTE**: Asegúrate de que tenga acceso a la misma `REDIS_URL` y `DATABASE_URL`

### F. Compartir variables entre servicios
Railway permite compartir variables entre servicios:
1. Ve a la pestaña de **Variables**
2. Haz click en **"Reference"** para referenciar las variables de Redis y PostgreSQL
3. Selecciona la variable `REDIS_URL` del servicio Redis
4. Selecciona la variable `DATABASE_URL` del servicio PostgreSQL

## 5. Migraciones (Automáticas con Release Process)

### ✅ Configuración Automática (Recomendado)

Este proyecto está configurado para ejecutar migraciones automáticamente antes de cada deploy usando el **Release Process** de Railway:

- El `Procfile` incluye: `release: bash migrate.sh`
- Railway ejecuta este comando **UNA VEZ** antes de iniciar los servicios
- Esto evita conflictos cuando tienes múltiples instancias del servidor

**No necesitas hacer nada manual**. Las migraciones se ejecutarán automáticamente en cada deploy.

### Verificar que las migraciones se ejecutaron:

1. Ve a tu servicio en Railway
2. Click en "Deployments" → Deployment más reciente
3. Busca los logs del proceso `release`:
   ```
   🔄 Iniciando proceso de migración...
   📦 Ejecutando migraciones de base de datos...
   👥 Verificando usuarios iniciales...
   📁 Recolectando archivos estáticos...
   ✅ Migración completada exitosamente
   ```

### Ejecutar migraciones manualmente (si es necesario):

Usando Railway CLI:
```bash
railway run bash migrate.sh
```

📖 **Para más detalles sobre el sistema de migraciones, consulta [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)**

## 6. Verificar que funciona

### Verificar Web:
```bash
curl https://tu-backend.up.railway.app/api/health/
```

### Verificar Celery Worker:
1. Ve al servicio Worker en Railway
2. Revisa los logs, deberías ver:
   ```
   [tasks]
     . inventory_app.tasks.generate_quotation_pdf

   celery@worker ready.
   ```

### Probar generación de PDF:
1. Crea una cotización desde el frontend
2. Solicita generar el PDF
3. Revisa los logs del Worker, deberías ver que procesa la tarea

## 7. Monitoreo

Para monitorear las tareas de Celery en producción, revisa los logs del servicio Worker en Railway:
- Ve al servicio `qualitycore-backend-worker`
- Click en **"Logs"**
- Verás las tareas siendo procesadas en tiempo real

## 8. Troubleshooting

### Error: "Connection refused" a Redis
- Verifica que `REDIS_URL` esté configurada en AMBOS servicios (Web y Worker)
- Asegúrate de que el servicio Redis esté corriendo

### Worker no procesa tareas
- Verifica que el Worker esté corriendo (revisa logs)
- Verifica que AMBOS servicios (Web y Worker) usen la misma `REDIS_URL`
- Reinicia el servicio Worker

### Tareas quedan en estado PENDING
- El Worker probablemente no está corriendo o no puede conectarse a Redis
- Revisa los logs del Worker

## 9. Arquitectura final

```
Railway Project
├── PostgreSQL Database (provee DATABASE_URL)
├── Redis (provee REDIS_URL)
├── Web Service (Django/Gunicorn)
│   └── Usa: DATABASE_URL, REDIS_URL
└── Worker Service (Celery)
    └── Usa: DATABASE_URL, REDIS_URL
```

## Notas importantes

- **Costos**: Redis y el Worker consumirán recursos adicionales en Railway
- **Escalabilidad**: Puedes crear múltiples workers si necesitas procesar más tareas
- **Logs**: Revisa logs regularmente para detectar problemas
- **Environment**: Asegúrate de que DEBUG=False en producción
