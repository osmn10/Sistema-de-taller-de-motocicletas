"""Lógica de negocio (services) para la gestión de citas."""

import logging
from datetime import date, datetime, time, timedelta

from django.conf import settings

from apps.core.emails import enviar_correo_html
from apps.usuarios.models import Mecanico

from .models import Cita, EnvioCorreo, EstadoCita
from .totales import calcular_detalle_cita
from .ticket_pdf import generar_ticket_pdf


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Disponibilidad de mecánicos (reasignación de citas)
# ---------------------------------------------------------------------------
# Tipos de estado en los que una cita ocupa el tiempo del mecánico.
TIPOS_ACTIVOS = (EstadoCita.TIPO_INICIO, EstadoCita.TIPO_PROCESO)


def _rango(cita: Cita) -> tuple[datetime, datetime]:
    """Inicio y fin de la cita según la duración de sus servicios."""
    inicio = datetime.combine(cita.fecha, cita.hora)
    minutos = sum(sc.servicio.duracion_estimada for sc in cita.serviciocita_set.all())
    return inicio, inicio + timedelta(minutes=minutos)


def _citas_que_se_cruzan(cita: Cita, **filtros):
    """Citas activas con mecánico que se cruzan con el horario de ``cita``."""
    inicio, fin = _rango(cita)
    otras = (
        Cita.objects.filter(fecha=cita.fecha, estado__tipo__in=TIPOS_ACTIVOS, mecanico__isnull=False, **filtros)
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


def _registrar_envio(cita, tipo, asunto, enviado, envio=None, error='',
                     fecha_anterior=None, hora_anterior=None):
    """HU031: deja constancia del envío. Con ``envio`` actualiza ese registro (reintento)."""
    if enviado:
        estado, error = EnvioCorreo.ESTADO_ENVIADO, ''
    else:
        estado = EnvioCorreo.ESTADO_FALLIDO
        error = error or 'El servicio de correo no respondió o rechazó el mensaje.'
    try:
        if envio is None:
            EnvioCorreo.objects.create(
                cita=cita, tipo=tipo, destinatario=cita.cliente.email,
                asunto=asunto[:200], estado=estado, error=error[:255],
                fecha_anterior=fecha_anterior, hora_anterior=hora_anterior,
            )
        else:
            envio.destinatario = cita.cliente.email
            envio.asunto = asunto[:200]
            envio.estado = estado
            envio.error = error[:255]
            envio.intentos += 1
            envio.save()
    except Exception:
        # el registro nunca debe tumbar la operación de la cita
        logger.exception('No se pudo registrar el envío de correo de la cita #%s.', cita.id)


def notificar_cita_agendada(cita_id: int, envio: EnvioCorreo | None = None) -> bool:
    """Envía al cliente la constancia inicial de su cita pendiente."""

    cita, servicios = _cita_con_detalles(cita_id)
    asunto = f'Cita #{cita.id} agendada - {settings.TALLER_NOMBRE}'
    enviado = enviar_correo_html(
        asunto=asunto,
        plantilla='emails/citas/cita_agendada.html',
        contexto={'cita': cita, 'servicios': servicios},
        destinatarios=[cita.cliente.email],
    )
    _registrar_envio(cita, EnvioCorreo.TIPO_AGENDADA, asunto, enviado, envio)
    return enviado


def notificar_cita_confirmada(cita_id: int, envio: EnvioCorreo | None = None) -> bool:
    """Informa al cliente que el taller confirmó su cita."""

    cita, servicios = _cita_con_detalles(cita_id)
    asunto = f'Cita #{cita.id} confirmada - {settings.TALLER_NOMBRE}'
    enviado = enviar_correo_html(
        asunto=asunto,
        plantilla='emails/citas/cita_confirmada.html',
        contexto={'cita': cita, 'servicios': servicios},
        destinatarios=[cita.cliente.email],
    )
    _registrar_envio(cita, EnvioCorreo.TIPO_CONFIRMADA, asunto, enviado, envio)
    return enviado


def notificar_cita_cancelada(cita_id: int, envio: EnvioCorreo | None = None) -> bool:
    """Confirma al cliente que su cita quedó cancelada."""

    cita, servicios = _cita_con_detalles(cita_id)
    asunto = f'Cita #{cita.id} cancelada - {settings.TALLER_NOMBRE}'
    enviado = enviar_correo_html(
        asunto=asunto,
        plantilla='emails/citas/cita_cancelada.html',
        contexto={'cita': cita, 'servicios': servicios},
        destinatarios=[cita.cliente.email],
    )
    _registrar_envio(cita, EnvioCorreo.TIPO_CANCELADA, asunto, enviado, envio)
    return enviado


def notificar_cita_reagendada(
    cita_id: int,
    fecha_anterior: date,
    hora_anterior: time,
    envio: EnvioCorreo | None = None,
) -> bool:
    """Informa al cliente el cambio de fecha/hora de una cita existente."""

    cita, servicios = _cita_con_detalles(cita_id)
    asunto = f'Cita #{cita.id} reagendada - {settings.TALLER_NOMBRE}'
    enviado = enviar_correo_html(
        asunto=asunto,
        plantilla='emails/citas/cita_reagendada.html',
        contexto={
            'cita': cita,
            'servicios': servicios,
            'fecha_anterior': fecha_anterior,
            'hora_anterior': hora_anterior,
        },
        destinatarios=[cita.cliente.email],
    )
    _registrar_envio(cita, EnvioCorreo.TIPO_REAGENDADA, asunto, enviado, envio,
                     fecha_anterior=fecha_anterior, hora_anterior=hora_anterior)
    return enviado


def notificar_cita_completada(cita_id: int, envio: EnvioCorreo | None = None) -> bool:
    """V2SCRUM-33: envía el correo de cierre con el ticket PDF adjunto.

    Usa la misma fuente de verdad que el ticket y el historial del cliente
    (``calcular_detalle_cita``, V2SCRUM-27). Si por algún motivo el total no
    se puede calcular con confianza (``errores`` no vacío), no se envía un
    monto definitivo: se registra y se omite el envío, sin bloquear el
    cierre de la cita, que ya ocurrió antes de llamar a esta función.
    """

    cita, servicios = _cita_con_detalles(cita_id)
    detalle = calcular_detalle_cita(cita)
    asunto = f'Cita #{cita.id} completada - {settings.TALLER_NOMBRE}'

    if detalle['errores']:
        logger.error(
            'No se envía el correo de cierre de la cita #%s: %s',
            cita_id, '; '.join(detalle['errores']),
        )
        _registrar_envio(cita, EnvioCorreo.TIPO_COMPLETADA, asunto, False, envio,
                         error='No se pudo calcular el total de la cita.')
        return False

    pdf_bytes = generar_ticket_pdf(cita, detalle)

    enviado = enviar_correo_html(
        asunto=asunto,
        plantilla='emails/citas/cita_completada.html',
        contexto={'cita': cita, 'servicios': servicios, 'detalle': detalle},
        destinatarios=[cita.cliente.email],
        adjuntos=[(f'ticket_cita_{cita.id}.pdf', pdf_bytes, 'application/pdf')],
    )
    _registrar_envio(cita, EnvioCorreo.TIPO_COMPLETADA, asunto, enviado, envio)
    return enviado


def reintentar_envio(envio: EnvioCorreo) -> bool:
    """HU031: vuelve a armar el correo con los datos actuales de la cita y lo envía."""
    if envio.tipo == EnvioCorreo.TIPO_AGENDADA:
        return notificar_cita_agendada(envio.cita_id, envio=envio)
    if envio.tipo == EnvioCorreo.TIPO_CONFIRMADA:
        return notificar_cita_confirmada(envio.cita_id, envio=envio)
    if envio.tipo == EnvioCorreo.TIPO_CANCELADA:
        return notificar_cita_cancelada(envio.cita_id, envio=envio)
    if envio.tipo == EnvioCorreo.TIPO_REAGENDADA:
        return notificar_cita_reagendada(envio.cita_id, envio.fecha_anterior, envio.hora_anterior, envio=envio)
    if envio.tipo == EnvioCorreo.TIPO_COMPLETADA:
        return notificar_cita_completada(envio.cita_id, envio=envio)
    return False
