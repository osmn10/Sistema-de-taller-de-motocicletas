# Sistema de Taller de Motocicletas

## Sobre el proyecto

Sistema web para la gestión integral de un taller de motocicletas. Permite a los clientes agendar citas en línea para servicios de mantenimiento y reparación, mientras que al personal del taller le brinda herramientas para administrar el catálogo de servicios, el inventario de productos y repuestos, los horarios de atención, las citas y el historial de cada motocicleta atendida.

El sistema contempla tres tipos de usuarios:

- **Cliente** — se registra de forma autónoma, gestiona sus motocicletas y agenda sus citas.
- **Mecánico** — usuario interno, atiende las citas asignadas y registra el avance de los servicios.
- **Administrador** — gestiona usuarios, catálogos, horarios y operación general del taller.

## Stack

El backend se desarrolla con **Django 5** siguiendo el patrón MVT con arquitectura modular por apps. El frontend utiliza **HTML5, CSS3, JavaScript y Bootstrap 5**. La base de datos es **SQLite** en desarrollo y **PostgreSQL** en producción. El control de versiones se maneja con **Git y GitHub**.

### Dependencias principales

- `Django 5.x` — framework web.
- `python-decouple` — lectura de variables de entorno desde `.env`.
- `dj-database-url` — configuración de base de datos vía URL en producción.
- `django-bootstrap5` — integración de Bootstrap 5 con formularios.
- `Pillow` — soporte para campos de imagen.
- `psycopg2-binary` — driver de PostgreSQL (solo producción, comentado en `requirements.txt`).

## Estructura de carpetas

```
taller-motos/
├── config/                 # Proyecto Django (settings, urls, wsgi, asgi)
│   ├── settings/
│   │   ├── base.py         # Configuración compartida
│   │   ├── development.py  # SQLite, DEBUG=True
│   │   └── production.py   # PostgreSQL vía DATABASE_URL
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/                   # Apps del dominio
│   ├── core/               # Base compartida (validators, mixins, base.html)
│   ├── usuarios/           # Usuario personalizado, managers, permisos
│   ├── vehiculos/          # Motocicletas de los clientes
│   ├── servicios/          # Catálogo de servicios del taller
│   ├── productos/          # Inventario y repuestos
│   ├── citas/              # Reservas y agenda (services.py)
│   └── configuracion/      # Parámetros del sistema
├── static/                 # css, js, images
├── media/                  # Archivos subidos por usuarios
├── docs/                   # Documentación del proyecto
│   └── buenas-practicas/   # Guías para el equipo
├── scripts/                # Scripts auxiliares
├── manage.py
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Guía de instalación

Pasos para clonar el repositorio y dejarlo corriendo localmente.

### 1. Requisitos previos

- **Python 3.12 o superior** instalado en el sistema.
- **Git** instalado y configurado con tu nombre y correo.
- Editor de código (recomendado: VS Code o PyCharm).

Verificar instalación:

```bash
python3 --version
git --version
```

### 2. Clonar el repositorio

```bash
git clone https://github.com/osmn10/Sistema-de-taller-de-motocicletas.git
cd Sistema-de-taller-de-motocicletas
```

### 3. Crear el entorno virtual

El entorno virtual aísla las dependencias del proyecto del sistema.

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (CMD)
python -m venv venv
venv\Scripts\activate

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

Cuando el entorno está activo se muestra `(venv)` al inicio del prompt.

### 4. Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configurar variables de entorno

```bash
cp .env.example .env     # macOS / Linux
copy .env.example .env   # Windows
```

Editar el archivo `.env` y reemplazar el valor de `SECRET_KEY` por una cadena aleatoria propia. Una forma rápida de generar una clave:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 6. Aplicar migraciones de base de datos

```bash
python manage.py migrate
```

Esto crea el archivo `db.sqlite3` con todas las tablas iniciales.

### 7. Crear un superusuario (acceso al panel admin)

```bash
python manage.py createsuperuser
```

Pide nombre de usuario, correo y contraseña.

### 8. Levantar el servidor de desarrollo

```bash
python manage.py runserver
```

La aplicación queda disponible en `http://127.0.0.1:8000/`.
El panel admin en `http://127.0.0.1:8000/admin/`.

Para detener el servidor: `Ctrl + C`.

---

## Comandos Python / Django más usados

### Entorno virtual

```bash
# Activar
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows

# Desactivar
deactivate

# Listar paquetes instalados
pip list

# Guardar dependencias actuales en requirements.txt
pip freeze > requirements.txt

# Instalar un paquete nuevo
pip install <nombre-paquete>
```

### Comandos de Django

```bash
# Servidor de desarrollo
python manage.py runserver               # puerto 8000 por defecto
python manage.py runserver 8080          # puerto personalizado
python manage.py runserver 0.0.0.0:8000  # accesible en red local

# Migraciones
python manage.py makemigrations          # detectar cambios en modelos
python manage.py makemigrations <app>    # solo una app específica
python manage.py migrate                 # aplicar migraciones a la BD
python manage.py showmigrations          # ver estado de las migraciones

# Usuarios y permisos
python manage.py createsuperuser
python manage.py changepassword <usuario>

# Shell interactiva con el ORM cargado
python manage.py shell

# Diagnóstico
python manage.py check                   # validar configuración
python manage.py check --deploy          # checks de producción

# Estáticos (solo producción)
python manage.py collectstatic

# Crear una nueva app
python manage.py startapp <nombre> apps/<nombre>
```

### Tests

```bash
python manage.py test                    # correr todos los tests
python manage.py test apps.usuarios      # solo una app
```

---

## Comandos Git más usados

### Configuración inicial (una sola vez por equipo)

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu-correo@ejemplo.com"
```

### Flujo de trabajo diario

```bash
# Ver estado del repositorio
git status

# Ver diferencias antes de hacer commit
git diff                       # cambios no agregados
git diff --staged              # cambios agregados pendientes de commit

# Agregar archivos al staging
git add <archivo>              # un archivo específico
git add carpeta/               # una carpeta
git add .                      # todo lo cambiado (usar con cuidado)

# Crear un commit
git commit -m "mensaje descriptivo del cambio"

# Subir cambios al repositorio remoto
git push

# Traer cambios del remoto
git pull
```

### Trabajo con ramas

```bash
# Ver ramas
git branch                     # ramas locales
git branch -a                  # locales y remotas

# Crear una rama y cambiarse a ella
git checkout -b feature/nombre-funcionalidad

# Cambiar entre ramas
git checkout main
git checkout feature/nombre-funcionalidad

# Subir una rama nueva al remoto
git push -u origin feature/nombre-funcionalidad

# Fusionar una rama en main (estando parado en main)
git checkout main
git pull
git merge feature/nombre-funcionalidad

# Borrar una rama local ya fusionada
git branch -d feature/nombre-funcionalidad
```

### Historial

```bash
git log                        # historial completo
git log --oneline              # historial resumido
git log --oneline --graph      # historial con gráfico de ramas
```

### Deshacer cambios

```bash
# Descartar cambios no agregados de un archivo
git checkout -- <archivo>

# Quitar un archivo del staging (sin perder los cambios)
git restore --staged <archivo>

# Modificar el mensaje del último commit (antes de pushearlo)
git commit --amend -m "nuevo mensaje"
```

---

## Configuración por entorno

- **`config.settings.development`** (por defecto en `manage.py`): SQLite y `DEBUG=True`.
- **`config.settings.production`**: PostgreSQL vía `DATABASE_URL`, `DEBUG=False`, flags de seguridad activos. Antes de desplegar, descomentar `psycopg2-binary` en `requirements.txt`.

Para forzar el módulo de settings desde la línea de comandos:

```bash
export DJANGO_SETTINGS_MODULE=config.settings.production   # macOS / Linux
set DJANGO_SETTINGS_MODULE=config.settings.production      # Windows CMD
```

---

## Buenas prácticas

Antes de empezar a contribuir, leer las guías del equipo en [`docs/buenas-practicas/`](docs/buenas-practicas/):

- [`seguridad.md`](docs/buenas-practicas/seguridad.md) — cómo evitar filtrar información personal o credenciales.
- [`desarrollo.md`](docs/buenas-practicas/desarrollo.md) — flujo de Git, estilo de código y convenciones del proyecto.
