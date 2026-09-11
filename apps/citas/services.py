"""Lógica de negocio (services) para la gestión de citas."""

from datetime import date, time

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


def notificar_cita_cancelada(cita_id: int) -> bool:
    """Confirma al cliente que su cita quedó cancelada."""

    cita, servicios = _cita_con_detalles(cita_id)
    resultado = enviar_correo_html(
        asunto=f'Cita #{cita.id} cancelada - {settings.TALLER_NOMBRE}',
        plantilla='emails/citas/cita_cancelada.html',
        contexto={'cita': cita, 'servicios': servicios},
        destinatarios=[cita.cliente.email],
    )
    print(f'[DEBUG] notificar_cita_cancelada(cita_id={cita_id}) -> {resultado}')
    return resultado


def notificar_cita_reagendada(
    cita_id: int,
    fecha_anterior: date,
    hora_anterior: time,
) -> bool:
    """Informa al cliente el cambio de fecha/hora de una cita existente."""

    cita, servicios = _cita_con_detalles(cita_id)
    resultado = enviar_correo_html(
        asunto=f'Cita #{cita.id} reagendada - {settings.TALLER_NOMBRE}',
        plantilla='emails/citas/cita_reagendada.html',
        contexto={
            'cita': cita,
            'servicios': servicios,
            'fecha_anterior': fecha_anterior,
            'hora_anterior': hora_anterior,
        },
        destinatarios=[cita.cliente.email],
    )
    print(f'[DEBUG] notificar_cita_reagendada(cita_id={cita_id}) -> {resultado}')
    return resultado