# 📦 QualityCore Services - Sistema de Inventario (Backend)

Sistema de gestión de inventario desarrollado con Django y Django REST Framework. Incluye control de stock en tiempo real, generación de cotizaciones, reportes en PDF, alertas automáticas y gestión de usuarios con roles.

---

## 🛠️ Stack Tecnológico

- **Framework:** Django 5.2.2
- **API:** Django REST Framework 3.16.0
- **Base de Datos:** PostgreSQL (psycopg2-binary 2.9.10)
- **Servidor:** Gunicorn 22.0.0
- **Almacenamiento de Imágenes:** Cloudinary (opcional)
- **Generación de PDFs:** ReportLab 4.4.2
- **Email:** SMTP (Gmail, etc.)
- **Lenguaje:** Python 3.11+
- **Timezone:** America/Guayaquil (Ecuador)

---

## 📋 Requisitos Previos

- Python 3.11 o superior
- PostgreSQL 12 o superior
- pip (gestor de paquetes de Python)
- Cuenta de Gmail con App Password (para envío de emails)
- Cuenta de Cloudinary (opcional, para imágenes de productos)

---

## 🔧 Instalación y Configuración

### 1. Clonar el Repositorio

```bash
git clone <url-del-repositorio>
cd qualitycore-inventory-backend
```

---

### 2. Crear y Activar Ambiente Virtual

#### Ubuntu Linux / MacOS

**Instalar gestor de ambientes virtuales:**
```bash
sudo apt install python3-venv
```

**Crear ambiente virtual:**
```bash
python3 -m venv .venv
```

**Activar ambiente virtual:**
```bash
source .venv/bin/activate
```

**Desactivar (cuando termines):**
```bash
deactivate
```

#### Windows

**Instalar gestor de ambientes virtuales:**
```bash
pip install virtualenv
```

**Crear ambiente virtual:**
```bash
python -m venv .venv
```

**Activar ambiente virtual:**
```bash
.\.venv\Scripts\Activate.ps1
```

**Desactivar (cuando termines):**
```bash
deactivate
```

---

### 3. Instalar Dependencias

#### Linux / MacOS
```bash
pip3 install -r requirements.txt
```

#### Windows
```bash
pip install -r requirements.txt
```

---



**Generar archivos de migración:**

#### Linux / MacOS
```bash
python3 manage.py makemigrations
```

#### Windows
```bash
python manage.py makemigrations
```

**Aplicar migraciones a la base de datos:**

#### Linux / MacOS
```bash
python3 manage.py migrate
```

#### Windows
```bash
python manage.py migrate
```

---

### 6. Crear Usuarios Super Administradores Iniciales

**Ejecutar comando personalizado:**

#### Linux / MacOS
```bash
python3 manage.py create_initial_users
```

#### Windows
```bash
python manage.py create_initial_users
```

**Salida esperada:**
```
✅ Superusuario creado: tu-email@gmail.com
============================================================
✅ Creados/Actualizados: 1
⏭️  Saltados: 0
============================================================
```

**Nota:** Este comando lee las credenciales del archivo `.env`. Los usuarios solo se crean si no existen previamente.

---

### 7. Iniciar Servidor de Desarrollo

#### Linux / MacOS
```bash
python3 manage.py runserver
```

#### Windows
```bash
python manage.py runserver
```

El servidor estará disponible en: **http://localhost:8000**

---

### Crear Superusuario Manualmente

#### Linux / MacOS
```bash
python3 manage.py createsuperuser
```

#### Windows
```bash
python manage.py createsuperuser
```

---

### Guardar Dependencias Actuales

#### Linux / MacOS
```bash
pip3 freeze > requirements.txt
```

#### Windows
```bash
pip freeze > requirements.txt
```

---

## 🎨 FRONTEND

### Instalación y Configuración

**Navegar al directorio del frontend:**
```bash
cd ./qualitycore-inventory-frontend
```

**Instalar dependencias:**
```bash
npm install
```

**Iniciar servidor de desarrollo:**
```bash
npm start
```

El frontend estará disponible en: **http://localhost:3000**

### Comandos Útiles del Frontend

**Instalar nuevas dependencias:**
```bash
npm install nombre-del-paquete
```

**Construir para producción:**
```bash
npm run build
```

**Ejecutar tests:**
```bash
npm test
```

**Verificar errores de linting:**
```bash
npm run lint
```

---

##  REDIS
```bash
docker run -d --name redis-qualitycore -p 6379:6379 redis:latest 
```
---
```bash
docker exec -it redis-qualitycore redis-cli ping 
```

## CELERY
```bash
cd .\qualitycore-inventory-backend\  
```
---
```bash
.venv\Scripts\python.exe -m celery -A inventory worker --loglevel=info --pool=solo
```

