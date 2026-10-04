"""
Configuración para entorno de producción.

Se espera leer DATABASE_URL (PostgreSQL) y SECRET_KEY desde el entorno.
"""

import dj_database_url
from decouple import config

from .base import *  # noqa: F401,F403


DEBUG = False

# En producción SMTP es el valor por defecto, salvo override del entorno. La clave se
# configura en el panel del hosting mediante EMAIL_HOST_PASSWORD.
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend',
)


# ---------------------------------------------------------------------------
# Base de datos: PostgreSQL vía DATABASE_URL (Neon.tech)
# ---------------------------------------------------------------------------
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True,
    )
}


# ---------------------------------------------------------------------------
# Archivos estáticos: WhiteNoise (sin servidor web aparte)
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    *MIDDLEWARE[1:],
]

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}


# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 días
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
