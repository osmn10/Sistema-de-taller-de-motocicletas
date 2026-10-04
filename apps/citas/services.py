"""Lógica de negocio (services) para la gestión de citas."""

import logging
from datetime import date, datetime, time, timedelta

from django.conf import settings

from apps.core.emails import enviar_correo_html
from apps.usuarios.models import Mecanico

from .models import Cita
from .totales import calcular_detalle_cita
from .ticket_pdf import generar_ticket_pdf


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Disponibilidad de mecánicos (reasignación de citas)
# ---------------------------------------------------------------------------
# Estados en los que una cita ocupa el tiempo del mecánico.
ESTADOS_ACTIVOS = (Cita.ESTADO_PENDIENTE, Cita.ESTADO_CONFIRMADA, Cita.ESTADO_EN_PROCESO)


def _rango(cita: Cita) -> tuple[datetime, datetime]:
    """Inicio y fin de la cita según la duración de sus servicios."""
    inicio = datetime.combine(cita.fecha, cita.hora)
    minutos = sum(sc.servicio.duracion_estimada for sc in cita.serviciocita_set.all())
    return inicio, inicio + timedelta(minutes=minutos)


def _citas_que_se_cruzan(cita: Cita, **filtros):
    """Citas activas con mecánico que se cruzan con el horario de ``cita``."""
    inicio, fin = _rango(cita)
    otras = (
        Cita.objects.filter(fecha=cita.fecha, estado__in=ESTADOS_ACTIVOS, mecanico__isnull=False, **filtros)
        .exclude(id=cita.id)
        .prefetch_related('serviciocita_set__servicio')
    )
    for otra in otras:
        otra_inicio, otra_fin = _rango(otra)
        if otra_inicio == inicio or (inicio < otra_fin and otra_inicio < fin):
            yield otra


def cita_en_conflicto(mecanico: Mecanico, cita: Cita) -> Cita | None:
    """Primera cita del mecánico que choca con ``cita``, o None si está libre."""
    return next(_citas_que_se_cruzan(cita, mecanico=mecanico), None)


def mecanicos_disponibles(cita: Cita):
    """Mecánicos activos libres en el horario de ``cita``."""
    ocupados = {otra.mecanico_id for otra in _citas_que_se_cruzan(cita)}
    return Mecanico.objects.filter(activo=True).exclude(pk__in=ocupados).order_by('apellido', 'nombre')


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
    return enviar_correo_html(
        asunto=f'Cita #{cita.id} cancelada - {settings.TALLER_NOMBRE}',
        plantilla='emails/citas/cita_cancelada.html',
        contexto={'cita': cita, 'servicios': servicios},
        destinatarios=[cita.cliente.email],
    )


def notificar_cita_reagendada(
    cita_id: int,
    fecha_anterior: date,
    hora_anterior: time,
) -> bool:
    """Informa al cliente el cambio de fecha/hora de una cita existente."""

    cita, servicios = _cita_con_detalles(cita_id)
    return enviar_correo_html(
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


def notificar_cita_completada(cita_id: int) -> bool:
    """V2SCRUM-33: envía el correo de cierre con el ticket PDF adjunto.

    Usa la misma fuente de verdad que el ticket y el historial del cliente
    (``calcular_detalle_cita``, V2SCRUM-27). Si por algún motivo el total no
    se puede calcular con confianza (``errores`` no vacío), no se envía un
    monto definitivo: se registra y se omite el envío, sin bloquear el
    cierre de la cita, que ya ocurrió antes de llamar a esta función.
    """

    cita, servicios = _cita_con_detalles(cita_id)
    detalle = calcular_detalle_cita(cita)

    if detalle['errores']:
        logger.error(
            'No se envía el correo de cierre de la cita #%s: %s',
            cita_id, '; '.join(detalle['errores']),
        )
        return False

    pdf_bytes = generar_ticket_pdf(cita, detalle)

    return enviar_correo_html(
        asunto=f'Cita #{cita.id} completada - {settings.TALLER_NOMBRE}',
        plantilla='emails/citas/cita_completada.html',
        contexto={'cita': cita, 'servicios': servicios, 'detalle': detalle},
        destinatarios=[cita.cliente.email],
        adjuntos=[(f'ticket_cita_{cita.id}.pdf', pdf_bytes, 'application/pdf')],
    )