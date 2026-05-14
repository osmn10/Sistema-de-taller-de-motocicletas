# Taller de Motos

Sistema web para la gestión de un taller de motocicletas: usuarios, vehículos,
servicios, productos, citas y configuración general.

Proyecto académico de la materia **Desarrollo de Sistemas Informáticos (DSI)**.

## Equipo

| Carnet | Integrante |
| ------ | ---------- |
| XX00000 | Integrante 1 |
| XX00000 | Integrante 2 |
| XX00000 | Integrante 3 |
| XX00000 | Integrante 4 |

> Reemplazar los carnets y nombres reales antes de entregar.

## Tecnologías

- Python 3.12+
- Django 5.x
- Bootstrap 5 (vía CDN)
- SQLite (desarrollo) / PostgreSQL (producción)
- `python-decouple` para variables de entorno
- `dj-database-url` para la URL de base de datos en producción
- `django-bootstrap5` para integración de formularios y componentes
- `Pillow` para campos de imagen

## Setup local (SQLite)

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd taller-motos

# 2. Crear y activar el entorno virtual
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env y colocar una SECRET_KEY propia

# 5. Aplicar migraciones y crear superusuario
python manage.py migrate
python manage.py createsuperuser

# 6. Levantar el servidor de desarrollo
python manage.py runserver
```

La aplicación quedará disponible en `http://127.0.0.1:8000/`.

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
│   ├── vehiculos/          # Motos / vehículos del cliente
│   ├── servicios/          # Servicios que ofrece el taller
│   ├── productos/          # Inventario y productos
│   ├── citas/              # Reservas y agenda (con services.py)
│   └── configuracion/      # Parámetros del sistema
├── static/                 # css, js, images
├── media/                  # Archivos subidos por usuarios
├── docs/                   # Documentación del proyecto
├── scripts/                # Scripts auxiliares
├── manage.py
├── requirements.txt
├── .env.example
└── .gitignore
```

## Configuración por entorno

- `config.settings.development` (por defecto en `manage.py`): SQLite y `DEBUG=True`.
- `config.settings.production`: PostgreSQL vía `DATABASE_URL`, `DEBUG=False`,
  flags de seguridad activos. Antes de desplegar, instalar `psycopg2-binary`
  descomentándolo en `requirements.txt`.

Para forzar el módulo de settings:

```bash
export DJANGO_SETTINGS_MODULE=config.settings.production
```
