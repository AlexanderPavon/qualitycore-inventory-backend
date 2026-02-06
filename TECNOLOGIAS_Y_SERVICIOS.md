# 🛠️ Tecnologías y Servicios - QualityCore Inventory System

Documentación completa de todas las tecnologías, frameworks y servicios externos utilizados en el sistema de inventario QualityCore.

---

## 📑 Tabla de Contenidos

1. [Backend Framework](#backend-framework)
2. [Base de Datos](#base-de-datos)
3. [Almacenamiento de Imágenes](#almacenamiento-de-imágenes)
4. [Tareas Asíncronas](#tareas-asíncronas)
5. [Monitoreo de Errores](#monitoreo-de-errores)
6. [Servidor de Producción](#servidor-de-producción)
7. [Email (SMTP)](#email-smtp)
8. [Plataforma de Deployment](#plataforma-de-deployment)
9. [Seguridad y Autenticación](#seguridad-y-autenticación)
10. [Generación de PDFs](#generación-de-pdfs)
11. [Frontend](#frontend)

---

## 🔧 Backend Framework

### **Django 5.2+**
**Propósito:** Framework web principal del backend

**¿Qué es?**
Django es un framework web de Python de alto nivel que fomenta el desarrollo rápido y el diseño limpio. Es el núcleo del backend de QualityCore.

**¿Por qué lo usamos?**
- ✅ Batteries included: ORM, autenticación, admin panel, etc.
- ✅ Seguridad integrada: Protección contra SQL injection, XSS, CSRF
- ✅ Escalable y maduro: Usado por Instagram, Pinterest, NASA
- ✅ Excelente documentación y comunidad activa

**Características principales:**
- ORM (Object-Relational Mapping) para interactuar con la base de datos sin SQL directo
- Sistema de autenticación robusto
- Panel de administración automático
- Migraciones de base de datos automatizadas
- Validación de datos integrada

**En el proyecto:**
```python
# Django se usa en todo el backend
# Modelos, vistas, serializers, middleware, etc.
```

**Documentación:** https://docs.djangoproject.com/

---

### **Django REST Framework (DRF) 3.16+**
**Propósito:** API RESTful para comunicación frontend-backend

**¿Qué es?**
Extensión de Django que facilita la creación de APIs RESTful con serialización, autenticación y vistas basadas en clases.

**¿Por qué lo usamos?**
- ✅ Integración perfecta con Django
- ✅ Serialización automática de modelos a JSON
- ✅ Autenticación por tokens
- ✅ Paginación y filtrado built-in
- ✅ Navegable API (interfaz web para testing)

**En el proyecto:**
```python
# Serializers para convertir modelos a JSON
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

# Vistas API
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
```

**Documentación:** https://www.django-rest-framework.org/

---

## 💾 Base de Datos

### **PostgreSQL 16+**
**Propósito:** Base de datos relacional principal

**¿Qué es?**
PostgreSQL es un sistema de gestión de bases de datos relacional de código abierto, conocido por su robustez, rendimiento y cumplimiento de estándares SQL.

**¿Por qué lo usamos?**
- ✅ ACID compliant (Atomicidad, Consistencia, Aislamiento, Durabilidad)
- ✅ Soporte para JSON/JSONB (datos semi-estructurados)
- ✅ Excelente rendimiento en consultas complejas
- ✅ Integridad referencial y constraints
- ✅ Escalabilidad horizontal y vertical

**En el proyecto:**
- Almacena todos los datos: productos, usuarios, movimientos, cotizaciones, etc.
- Relaciones entre tablas con foreign keys
- Índices para búsquedas rápidas
- Soft deletes (registros marcados como eliminados, no borrados físicamente)

**Configuración:**
```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'inventorydb',
        'USER': 'postgres',
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': '5432',
    }
}
```

**Documentación:** https://www.postgresql.org/docs/

---

### **AWS RDS (Amazon Relational Database Service)**
**Propósito:** Hosting de PostgreSQL en producción

**¿Qué es?**
Servicio administrado de Amazon Web Services que facilita configurar, operar y escalar bases de datos relacionales en la nube.

**¿Por qué lo usamos?**
- ✅ Backups automáticos diarios
- ✅ Alta disponibilidad con Multi-AZ
- ✅ Escalabilidad sin downtime
- ✅ Monitoreo integrado con CloudWatch
- ✅ Actualizaciones automáticas de seguridad
- ✅ No necesitas administrar el servidor físico

**Características en producción:**
- **Instance type:** db.t3.micro (plan gratuito)
- **Storage:** 20 GB SSD (escalable)
- **Backups:** Retención de 7 días
- **Región:** us-east-2 (Ohio)
- **SSL/TLS:** Conexiones encriptadas

**Conexión:**
```
Host: inventorydb.cr8mw64yqo3p.us-east-2.rds.amazonaws.com
Port: 5432
Database: inventorydb
User: postgres
Password: [Configurado en .env]
```

**Costos:**
- Free Tier: 750 horas/mes por 12 meses
- Después: ~$15-20/mes (db.t3.micro)

**Documentación:** https://aws.amazon.com/rds/

---

## 🖼️ Almacenamiento de Imágenes

### **Cloudinary**
**Propósito:** CDN y almacenamiento de imágenes de productos

**¿Qué es?**
Plataforma en la nube para gestión de imágenes y videos. Ofrece almacenamiento, transformación automática, optimización y entrega vía CDN global.

**¿Por qué lo usamos?**
- ✅ Railway tiene almacenamiento efímero (se borra en cada deploy)
- ✅ CDN global para carga rápida desde cualquier país
- ✅ Transformaciones automáticas (resize, crop, optimización)
- ✅ Formatos modernos (WebP, AVIF) automáticos
- ✅ Respaldos y redundancia incluidos
- ✅ Plan gratuito generoso

**Características:**
- **Almacenamiento:** 25 GB (plan gratuito)
- **Bandwidth:** 25 GB/mes
- **Transformaciones:** Ilimitadas
- **CDN:** 350+ ubicaciones globales
- **Formatos:** JPG, PNG, WebP, AVIF, SVG

**En el proyecto:**
```python
# settings.py
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
}

# models/product.py
class Product(models.Model):
    image = models.ImageField(
        upload_to="products/",
        validators=[validate_image_size, validate_image_dimensions]
    )
```

**Flujo de subida:**
1. Usuario sube imagen desde frontend
2. Backend valida tamaño (max 2MB) y dimensiones (300-2000px)
3. Django guarda en Cloudinary automáticamente
4. Cloudinary optimiza y convierte a formatos modernos
5. Retorna URL permanente con CDN

**URLs generadas:**
```
https://res.cloudinary.com/tu_cloud_name/image/upload/v1234567890/products/imagen.jpg
```

**Dashboard:** https://cloudinary.com/console/

**Documentación:** https://cloudinary.com/documentation/django_integration

---

## ⚙️ Tareas Asíncronas

### **Celery 5.6+**
**Propósito:** Ejecución de tareas en segundo plano

**¿Qué es?**
Sistema de cola de tareas distribuido que permite ejecutar operaciones pesadas de forma asíncrona, sin bloquear las peticiones HTTP.

**¿Por qué lo usamos?**
- ✅ Generación de PDFs sin ralentizar el servidor
- ✅ Envío de emails en segundo plano
- ✅ Procesamiento de imágenes pesadas
- ✅ Tareas programadas (cron jobs)
- ✅ Reintentos automáticos en caso de fallos

**Tareas implementadas:**

1. **Generación de PDFs de cotizaciones** (`generate_quotation_pdf`)
   - Duración: 2-5 segundos
   - Se ejecuta en segundo plano mientras el usuario continúa navegando
   - Reintenta hasta 3 veces si falla

2. **Generación de reportes de movimientos** (`generate_movements_report_pdf`)
   - Duración: 3-10 segundos (dependiendo de cantidad de datos)
   - Procesa hasta 50 movimientos
   - Genera PDF con gráficos y tablas

**Configuración:**
```python
# settings.py
CELERY_BROKER_URL = env('REDIS_URL')  # Redis como broker
CELERY_RESULT_BACKEND = env('REDIS_URL')
CELERY_TASK_SERIALIZER = 'json'
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos máximo por tarea
CELERY_RESULT_EXPIRES = 3600  # Resultados expiran en 1 hora
```

**Uso en el código:**
```python
# tasks.py
@shared_task(bind=True, max_retries=3)
def generate_quotation_pdf(self, quotation_id, user_id):
    try:
        # Generar PDF...
        return filepath
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

# Llamada desde la vista
task = generate_quotation_pdf.delay(quotation.id, user.id)
```

**Monitoreo:**
- Logs en `logs/celery.log`
- Comandos: `celery -A inventory inspect active` (ver tareas activas)

**Documentación:** https://docs.celeryq.dev/

---

### **Redis 7.1+**
**Propósito:** Message broker para Celery

**¿Qué es?**
Base de datos en memoria ultra-rápida que actúa como intermediario entre Django y Celery para gestionar la cola de tareas.

**¿Por qué lo usamos?**
- ✅ Extremadamente rápido (operaciones en microsegundos)
- ✅ Persistencia opcional (respaldos en disco)
- ✅ Pub/Sub para comunicación en tiempo real
- ✅ Compatible nativamente con Celery
- ✅ Railway lo proporciona automáticamente

**Flujo de trabajo:**
1. Django crea una tarea y la envía a Redis
2. Redis guarda la tarea en una cola
3. Celery worker toma la tarea de la cola
4. Worker ejecuta la tarea
5. Resultado se guarda de vuelta en Redis
6. Django puede consultar el estado/resultado

**En Railway:**
- Railway proporciona Redis automáticamente vía variable `REDIS_URL`
- No necesitas configurar nada manualmente
- Incluido en el plan gratuito

**Desarrollo local:**
```bash
# Instalar Redis en Windows con Chocolatey
choco install redis-64

# Iniciar Redis
redis-server

# Verificar conexión
redis-cli ping  # Responde: PONG
```

**Documentación:** https://redis.io/docs/

---

## 🚨 Monitoreo de Errores

### **Sentry**
**Propósito:** Monitoreo de errores en tiempo real y alertas

**¿Qué es?**
Plataforma de monitoreo de aplicaciones que captura errores, excepciones y problemas de rendimiento en tiempo real, enviando alertas inmediatas.

**¿Por qué lo usamos?**
- ✅ Alertas instantáneas por email cuando algo falla
- ✅ Stack traces completos con contexto del error
- ✅ Información del usuario afectado (ID, email, IP)
- ✅ Breadcrumbs (historial de acciones antes del error)
- ✅ Agrupa errores similares para detectar patrones
- ✅ Monitoreo de performance (endpoints lentos)

**Diferencia con logs:**
| Característica | Logs | Sentry |
|----------------|------|--------|
| Búsqueda | Manual | Automática |
| Alertas | No | Sí (email/Slack) |
| Agrupación | No | Sí |
| Contexto usuario | Limitado | Completo |
| Performance | No | Sí |

**Lo que captura:**
- Errores 500 (Internal Server Error)
- Excepciones no capturadas
- Errores en tareas Celery
- Queries lentas de base de datos
- Requests HTTP fallidos
- Variables locales en el momento del error

**Configuración:**
```python
# settings.py (solo en producción)
if not DEBUG:
    sentry_sdk.init(
        dsn=env('SENTRY_DSN'),
        integrations=[
            DjangoIntegration(),  # Captura errores de Django
            CeleryIntegration(),  # Captura errores de Celery
        ],
        traces_sample_rate=0.3,  # Monitorea 30% de las transacciones
        profiles_sample_rate=0.3,
        environment='production',
        send_default_pii=False,  # No envía datos personales
    )
```

**Ejemplo de error capturado:**
```
ZeroDivisionError: division by zero
  File "views/product_view.py", line 45, in calculate_stock
    ratio = current / 0

Context:
  User ID: 123
  User Email: user@example.com
  Request: POST /api/products/
  Variables:
    current = 100
    minimum = 20
```

**Plan gratuito:**
- 5,000 errores/mes
- 10,000 eventos de performance/mes
- 30 días de retención
- Alertas por email

**Dashboard:** https://sentry.io/

**Documentación:** https://docs.sentry.io/platforms/python/integrations/django/

---

## 📊 Logs del Sistema

### **Logging (Python + Django)**
**Propósito:** Registro de eventos para debugging y auditoría

**4 tipos de logs configurados:**

1. **audit.log** - Auditoría de acciones importantes
   - Login/logout de usuarios
   - Creación/modificación/eliminación de registros
   - Cambios de permisos
   - Rotación: Cada 10 MB, mantiene 5 backups

2. **errors.log** - Errores y excepciones
   - Errores 500
   - Excepciones capturadas
   - Fallos de validación críticos
   - Rotación: Cada 10 MB, mantiene 5 backups

3. **general.log** - Eventos generales del sistema
   - Inicios de servidor
   - Configuraciones cargadas
   - Warnings y avisos
   - Rotación: Cada 10 MB, mantiene 5 backups

4. **inventory.log** - Eventos específicos de inventario
   - Movimientos de stock
   - Cotizaciones generadas
   - Reportes creados
   - Rotación: Cada 10 MB, mantiene 3 backups

**Ubicación:** `qualitycore-inventory-backend/logs/`

**Formato:**
```
2025-01-15 14:30:45,123 [INFO] inventory_app.views.product_view: Producto 'Laptop HP' creado por usuario admin@example.com
```

**En Railway:**
- Los logs se integran automáticamente con el dashboard de Railway
- Se pueden ver en tiempo real: Deployments > Logs
- Se mantienen por 7 días en el plan gratuito

**Configuración:**
```python
# settings.py
LOGGING = {
    'handlers': {
        'audit_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/audit.log',
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 5,
        },
    },
}
```

---

## 📄 Generación de PDFs

### **ReportLab 4.4+**
**Propósito:** Creación de documentos PDF dinámicos

**¿Qué es?**
Librería de Python para generar PDFs programáticamente con tablas, imágenes, gráficos y estilos personalizados.

**¿Por qué lo usamos?**
- ✅ Control total del diseño del PDF
- ✅ Renderizado rápido (1-3 segundos por PDF)
- ✅ Soporte para tablas complejas
- ✅ Imágenes y logos
- ✅ Estilos personalizables

**PDFs generados:**

1. **Cotizaciones (`quotation_ID_CLIENTE_FECHA.pdf`)**
   - Logo de la empresa
   - Datos del cliente y vendedor
   - Tabla de productos cotizados
   - Cálculo de subtotal, IVA (15%) y total
   - Observaciones opcionales
   - Nota: "Cotización válida por 30 días"

2. **Reportes de movimientos (`movements_report_FECHA.pdf`)**
   - Últimos 50 movimientos de inventario
   - Tabla con: fecha, tipo, producto, cantidad, stock
   - Generado con fecha y hora actual

**Flujo de generación:**
1. Usuario solicita PDF desde frontend
2. Backend crea tarea Celery asíncrona
3. ReportLab genera el PDF (2-5 segundos)
4. PDF se guarda en `media/reports/`
5. Se registra en modelo `Report` con referencia al usuario
6. Frontend descarga el PDF cuando está listo

**Ejemplo de código:**
```python
# tasks.py
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph

def generate_quotation_pdf(quotation_id, user_id):
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    elements = []

    # Logo
    img = Image(logo_path, width=90, height=40)
    elements.append(img)

    # Tabla de productos
    data = [["Producto", "Cantidad", "Precio", "Subtotal"]]
    for p in quotation.quoted_products.all():
        data.append([p.product.name, p.quantity, f"${p.unit_price}", f"${p.subtotal}"])

    table = Table(data)
    elements.append(table)

    doc.build(elements)
```

**Documentación:** https://www.reportlab.com/docs/reportlab-userguide.pdf

---

## 🌐 Servidor de Producción

### **Gunicorn 22.0+**
**Propósito:** Servidor WSGI HTTP para Python en producción

**¿Qué es?**
Gunicorn (Green Unicorn) es un servidor HTTP WSGI que ejecuta aplicaciones Django en producción de forma eficiente y escalable.

**¿Por qué lo usamos?**
- ✅ Multiproceso (workers paralelos)
- ✅ Manejo eficiente de conexiones concurrentes
- ✅ Auto-restart de workers si fallan
- ✅ Compatible con Django/Flask/cualquier WSGI
- ✅ Estándar de la industria

**Configuración en Railway:**
```bash
# Procfile
web: gunicorn inventory.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 120
worker: celery -A inventory worker --loglevel=info
```

**Workers:**
- **2 workers** en Railway (plan gratuito tiene CPU limitado)
- Cada worker puede manejar ~100-1000 requests/segundo (dependiendo de complejidad)
- Auto-restart si un worker falla

**En desarrollo local:**
- Se usa el servidor de desarrollo de Django: `python manage.py runserver`
- NO usar en producción (inseguro y lento)

**Documentación:** https://docs.gunicorn.org/

---

## 📧 Email (SMTP)

### **Gmail SMTP**
**Propósito:** Envío de emails (recuperación de contraseña, notificaciones)

**¿Qué es?**
Servicio SMTP de Gmail que permite enviar emails desde tu aplicación usando credenciales de Google.

**¿Por qué lo usamos?**
- ✅ Gratuito hasta 500 emails/día
- ✅ Confiable y rápido
- ✅ No requiere servidor SMTP propio
- ✅ Soporte de App Passwords (autenticación segura)

**Configuración:**
```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'tu_email@gmail.com'
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')  # App Password
DEFAULT_FROM_EMAIL = 'tu_email@gmail.com'
```

**Emails enviados:**
1. **Recuperación de contraseña**
   - Link temporal con token de 24 horas
   - Enviado cuando usuario solicita "Olvidé mi contraseña"

2. **Notificaciones de stock bajo** (opcional, si se implementa)
   - Alerta cuando producto llega a stock mínimo

**Obtener App Password:**
1. Ve a Google Account > Security
2. Activa "2-Step Verification"
3. App Passwords > Generate
4. Copia el password de 16 caracteres
5. Pégalo en `EMAIL_HOST_PASSWORD` en .env

**Límites:**
- 500 emails/día (Gmail gratuito)
- Para más: usar SendGrid, Mailgun o SES

**Documentación:** https://support.google.com/mail/answer/7126229

---

## 🚀 Plataforma de Deployment

### **Railway**
**Propósito:** Hosting del backend y servicios asociados

**¿Qué es?**
Plataforma moderna de deployment (como Heroku) que simplifica el despliegue de aplicaciones con auto-deploy desde GitHub, variables de entorno y servicios integrados.

**¿Por qué lo usamos?**
- ✅ Plan gratuito: $5 de crédito/mes (suficiente para desarrollo)
- ✅ Auto-deploy desde GitHub (push = deploy automático)
- ✅ Variables de entorno fáciles de configurar
- ✅ Redis incluido gratis
- ✅ Logs en tiempo real
- ✅ SSL/HTTPS automático
- ✅ Métricas de CPU, RAM, tráfico

**Servicios desplegados:**
1. **Backend Django** (`qualitycore-inventory-backend`)
   - 2 workers Gunicorn
   - 512 MB RAM
   - ~$3-4/mes

2. **Celery Worker**
   - Procesa tareas asíncronas
   - ~$1-2/mes

3. **Redis**
   - Incluido gratis
   - 100 MB almacenamiento

**Variables de entorno configuradas:**
```
DEBUG=False
SECRET_KEY=...
DB_HOST=inventorydb.cr8mw64yqo3p.us-east-2.rds.amazonaws.com
DB_NAME=inventorydb
DB_PASSWORD=...
CLOUDINARY_CLOUD_NAME=...
SENTRY_DSN=...
REDIS_URL=[Auto-generado por Railway]
```

**Flujo de deployment:**
1. Haces `git push origin main`
2. Railway detecta el cambio
3. Ejecuta `pip install -r requirements.txt`
4. Ejecuta migraciones: `python manage.py migrate`
5. Recolecta archivos estáticos: `python manage.py collectstatic --noinput`
6. Inicia Gunicorn: `gunicorn inventory.wsgi`
7. Deploy completo en 2-3 minutos

**Monitoreo:**
- Dashboard: https://railway.app/project/...
- Logs en tiempo real
- Métricas de uso
- Alertas de errores

**Costos:**
- Plan Developer: $5 crédito/mes gratis
- Uso típico: $3-5/mes (dentro del límite gratuito)
- Plan Pro: $20/mes si necesitas más

**Documentación:** https://docs.railway.app/

---

## 🔐 Seguridad y Autenticación

### **Django Authentication System**
**Propósito:** Gestión de usuarios y sesiones

**Características:**
- ✅ Hash de contraseñas con PBKDF2 (256,000 iteraciones)
- ✅ Protección contra brute force
- ✅ Validación de contraseñas complejas (custom validator)
- ✅ Tokens de sesión seguros
- ✅ CSRF protection automático

**Validador de contraseñas personalizado:**
```python
# validators.py
class ComplexPasswordValidator:
    """
    Requiere:
    - Mínimo 8 caracteres
    - Al menos 1 mayúscula
    - Al menos 1 minúscula
    - Al menos 1 número
    - Al menos 1 carácter especial
    """
```

**Autenticación en el API:**
- **Session-based authentication** para el panel de administración
- **Token authentication** potencial para frontend (si se implementa)

---

### **CORS (Cross-Origin Resource Sharing)**
**Propósito:** Permitir peticiones desde el frontend en diferente dominio

**Librería:** `django-cors-headers`

**Configuración:**
```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Frontend local
    "https://qualitycore-inventory-frontend-production.up.railway.app",  # Frontend producción
]
CORS_ALLOW_CREDENTIALS = True  # Permite cookies entre dominios
```

**Documentación:** https://github.com/adamchainz/django-cors-headers

---

### **Security Headers (Producción)**
**Propósito:** Proteger contra ataques comunes

**Headers configurados:**
```python
# Solo en producción (DEBUG=False)
SECURE_SSL_REDIRECT = True  # Fuerza HTTPS
SECURE_HSTS_SECONDS = 31536000  # HSTS por 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'  # Anti-clickjacking
SECURE_CONTENT_TYPE_NOSNIFF = True  # Anti-MIME sniffing
SESSION_COOKIE_SECURE = True  # Cookies solo HTTPS
CSRF_COOKIE_SECURE = True  # CSRF solo HTTPS
```

**Protecciones:**
- ✅ HTTPS obligatorio
- ✅ Cookies seguras (solo HTTPS)
- ✅ Prevención de clickjacking
- ✅ Prevención de MIME sniffing
- ✅ HSTS (navegadores recuerdan usar HTTPS siempre)

---

### **SSL/TLS Encryption**
**Propósito:** Encriptar comunicación cliente-servidor

**Implementación:**
- Railway proporciona SSL/TLS automáticamente
- Certificados Let's Encrypt renovados automáticamente
- Todas las conexiones usan HTTPS en producción
- Conexión a PostgreSQL encriptada con `sslmode=require`

---

## 🎨 Frontend

### **React 18+ (Vite)**
**Propósito:** Interfaz de usuario moderna y reactiva

**¿Qué es?**
React es una librería de JavaScript para construir interfaces de usuario basadas en componentes reutilizables.

**Stack del frontend:**
- **React 18+** - Librería principal
- **Vite** - Build tool ultrarrápido
- **React Router** - Navegación SPA
- **Axios** - Peticiones HTTP al backend
- **Tailwind CSS** - Estilos utility-first
- **Lucide React** - Iconos

**Características:**
- ✅ SPA (Single Page Application)
- ✅ Componentes reutilizables
- ✅ Estado global con Context API
- ✅ Validación de formularios
- ✅ Dark mode implementado
- ✅ Responsive design

**Estructura:**
```
qualitycore-inventory-frontend/
├── src/
│   ├── components/       # Componentes reutilizables
│   ├── pages/           # Páginas principales
│   ├── context/         # Estado global
│   ├── services/        # API calls
│   └── utils/           # Funciones helper
```

**Comunicación con backend:**
```javascript
// services/api.js
const API_URL = 'https://qualitycore-backend.up.railway.app/api'

export const getProducts = async () => {
  const response = await axios.get(`${API_URL}/products/`)
  return response.data
}
```

**Deployment:**
- Plataforma: Railway
- Build: `npm run build`
- Servidor: Nginx (servir archivos estáticos)

**Documentación:** https://react.dev/

---

## 📦 Dependencias Adicionales

### **psycopg2-binary**
**Propósito:** Adaptador PostgreSQL para Python
- Permite a Django conectarse a PostgreSQL
- Versión binary: No requiere compilación

### **django-environ**
**Propósito:** Gestión de variables de entorno
- Lee archivos `.env`
- Parsea tipos automáticamente (bool, int, list)

### **python-dateutil**
**Propósito:** Manejo avanzado de fechas
- Parsing de fechas en múltiples formatos
- Cálculos de diferencias de fechas

### **Pillow (PIL)**
**Propósito:** Procesamiento de imágenes
- Validación de dimensiones de imágenes
- Conversión de formatos
- Redimensionamiento

### **requests**
**Propósito:** Cliente HTTP para Python
- Llamadas a APIs externas
- Más simple que urllib

---

## 🔄 Flujo Completo del Sistema

### Flujo de una petición típica:

1. **Usuario hace login en React**
   ```
   Frontend (React) → POST /api/auth/login/ → Backend (Django)
   ```

2. **Backend autentica**
   ```
   Django verifica credenciales en PostgreSQL (AWS RDS)
   → Crea sesión → Retorna token/cookie
   ```

3. **Usuario crea un producto**
   ```
   React → POST /api/products/ con imagen
   → Django valida datos
   → Cloudinary almacena imagen
   → PostgreSQL guarda producto
   → Sentry monitorea (si hay error)
   → Log en audit.log
   ```

4. **Usuario genera cotización PDF**
   ```
   React → POST /api/quotations/generate-pdf/
   → Django crea tarea Celery
   → Envía tarea a Redis
   → Celery worker procesa
   → ReportLab genera PDF
   → Guarda en media/reports/
   → Frontend descarga PDF
   ```

5. **Error inesperado ocurre**
   ```
   Django captura excepción
   → Sentry registra error con contexto
   → Email enviado al admin
   → Log en errors.log
   → Usuario ve mensaje amigable
   ```

---

## 📊 Resumen de Costos Mensuales

| Servicio | Plan | Costo |
|----------|------|-------|
| Railway (Backend + Redis) | Developer | $5 crédito gratis |
| AWS RDS PostgreSQL | Free Tier (12 meses) | $0 (luego ~$15) |
| Cloudinary | Free Tier | $0 |
| Sentry | Developer | $0 |
| Gmail SMTP | Free | $0 |
| **TOTAL** | | **$0-5/mes** |

Después de 12 meses (cuando expira Free Tier de AWS):
- **$15-20/mes** (principalmente por AWS RDS)

---

## 🛡️ Mejores Prácticas Implementadas

✅ **Seguridad:**
- HTTPS en producción
- Contraseñas hasheadas con PBKDF2
- CSRF protection
- SQL injection prevention (ORM)
- XSS prevention (Django templates)
- Validación de entrada en frontend y backend

✅ **Performance:**
- Índices en base de datos
- Paginación (20 items por página)
- CDN para imágenes (Cloudinary)
- Tareas pesadas en background (Celery)
- Connection pooling (CONN_MAX_AGE)

✅ **Escalabilidad:**
- Soft deletes (no borra datos físicamente)
- Migraciones de BD versionadas
- Logs rotativos (no crecen infinitamente)
- Separación frontend-backend
- Stateless API (puede escalar horizontalmente)

✅ **Mantenibilidad:**
- Código modular
- Comentarios en español
- Documentación exhaustiva
- Logs detallados
- Monitoreo con Sentry

---

## 📚 Recursos de Aprendizaje

- **Django:** https://docs.djangoproject.com/
- **PostgreSQL:** https://www.postgresql.org/docs/
- **Celery:** https://docs.celeryq.dev/
- **React:** https://react.dev/
- **Railway:** https://docs.railway.app/
- **Cloudinary:** https://cloudinary.com/documentation/

---

## 🤝 Soporte

Si tienes preguntas sobre alguna tecnología o servicio:
1. Consulta la documentación oficial (links arriba)
2. Revisa los comentarios en el código
3. Consulta los logs del sistema
4. Contacta al equipo de desarrollo

---

**Última actualización:** Diciembre 2024
**Versión del sistema:** 1.0.0
**Autores:** Alexander Pavón, Alison Carrión
