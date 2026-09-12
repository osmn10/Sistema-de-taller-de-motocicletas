"""Infraestructura común para enviar correos HTML desde cualquier app."""

import logging
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


logger = logging.getLogger(__name__)

Adjunto = tuple[str, bytes, str]


def enviar_correo_html(
    *,
    asunto: str,
    plantilla: str,
    contexto: Mapping[str, Any],
    destinatarios: Sequence[str],
    adjuntos: Iterable[Adjunto] = (),
    propagar_error: bool = False,
) -> bool:
    """Renderiza y envía un correo, sin bloquear el negocio si el proveedor falla.

    ``propagar_error`` se reserva para comandos diagnósticos. Las vistas y los
    servicios de negocio deben conservar el valor ``False`` para que una caída
    del proveedor no impida agendar, confirmar o completar una cita.
    """

    correos = [correo.strip() for correo in destinatarios if correo.strip()]
    if not correos:
        logger.warning('Se omitió un correo sin destinatarios para: %s', asunto)
        return False

    contexto_completo = {
        **contexto,
        'taller_nombre': settings.TALLER_NOMBRE,
        'taller_telefono': settings.TALLER_TELEFONO,
        'taller_direccion': settings.TALLER_DIRECCION,
        'taller_email_contacto': settings.TALLER_EMAIL_CONTACTO,
    }

    try:
        cuerpo_html = render_to_string(plantilla, contexto_completo)
        mensaje = EmailMultiAlternatives(
            subject=asunto,
            body=strip_tags(cuerpo_html),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=correos,
        )
        mensaje.attach_alternative(cuerpo_html, 'text/html')

        for nombre, contenido, tipo_mime in adjuntos:
            mensaje.attach(nombre, contenido, tipo_mime)

        enviados = mensaje.send(fail_silently=False)
        if enviados != 1:
            logger.error('El backend no aceptó el correo "%s".', asunto)
            return False
        return True
    except Exception as error:
        # No registrar respuestas crudas del proveedor: pueden contener datos
        # sensibles. El asunto identifica la notificación y su cita.
        logger.error(
            'No se pudo enviar el correo "%s". Tipo de error: %s.',
            asunto,
            type(error).__name__,
        )
        if propagar_error:
            raise
        return False
