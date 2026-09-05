"""Lógica de negocio (services) para la gestión de citas."""

from django.conf import settings

from apps.core.emails import enviar_correo_html

from .models import Cita


def _cita_con_detalles(cita_id: int) -> tuple[Cita, list]:
    """Recupera la cita con los datos necesarios para una notificación."""

    cita = Cita.objects.select_related(
        'cliente',
        'motocicleta',
        'mecanico',
    ).get(id=cita_id)
    servicios = list(
        cita.serviciocita_set.select_related('servicio').order_by('id')
    )
    return cita, servicios


def notificar_cita_agendada(cita_id: int) -> bool:
    """Envía al cliente la constancia inicial de su cita pendiente."""

    cita, servicios = _cita_con_detalles(cita_id)
    return enviar_correo_html(
        asunto=f'Cita #{cita.id} agendada - {settings.TALLER_NOMBRE}',
        plantilla='emails/citas/cita_agendada.html',
        contexto={'cita': cita, 'servicios': servicios},
        destinatarios=[cita.cliente.email],
    )


def notificar_cita_confirmada(cita_id: int) -> bool:
    """Informa al cliente que el taller confirmó su cita."""

    cita, servicios = _cita_con_detalles(cita_id)
    return enviar_correo_html(
        asunto=f'Cita #{cita.id} confirmada - {settings.TALLER_NOMBRE}',
        plantilla='emails/citas/cita_confirmada.html',
        contexto={'cita': cita, 'servicios': servicios},
        destinatarios=[cita.cliente.email],
    )
