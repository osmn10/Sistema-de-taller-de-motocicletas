"""
Configuración para entorno local de desarrollo.

Usa SQLite por defecto para evitar requerir PostgreSQL al clonar el repo.
"""

from decouple import config

from .base import BASE_DIR, INSTALLED_APPS, MIDDLEWARE  # noqa: F401
from .base import *  # noqa: F401,F403


DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']


# ---------------------------------------------------------------------------
# Base de datos: SQLite local
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
