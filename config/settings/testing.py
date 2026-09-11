"""Configuración usada exclusivamente por las pruebas automatizadas."""

from .development import *  # noqa: F401,F403


# Los mensajes quedan disponibles en django.core.mail.outbox durante cada test.
# No requiere Internet, una cuenta de Resend ni una API key.
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
