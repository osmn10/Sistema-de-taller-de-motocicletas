"""V2SCRUM-39: cálculo del reporte de servicios del taller por período.

Reutiliza ``calcular_detalle_cita`` (V2SCRUM-27) como fuente de los
ingresos, igual que el ticket (V2SCRUM-30) y el dashboard (V2SCRUM-40).

Criterio de conteo: "servicios más solicitados" y "mecánico con más
servicios" cuentan todas las citas del período salvo las canceladas —
reflejan demanda, no solo lo ya cobrado. "Ingresos totales" solo
considera citas completadas, igual que el dashboard.
"""

from decimal import Decimal

from django.db.models import Count

from .models import Cita, ServicioCita
from .totales import calcular_detalle_cita


def calcular_reporte_servicios(desde, hasta, servicio_id=None, mecanico_dui=None):
    """Arma el reporte de servicios del taller en un rango de fechas.

    ``servicio_id`` y ``mecanico_dui`` son filtros opcionales: si se pasan,
    el reporte completo (KPIs incluidos) queda acotado a esa cita filtrada.
    """

    citas_periodo = Cita.objects.filter(fecha__gte=desde, fecha__lte=hasta)
    citas_activas = citas_periodo.exclude(estado=Cita.ESTADO_CANCELADA)

    if servicio_id:
        citas_activas = citas_activas.filter(servicios__id=servicio_id).distinct()
    if mecanico_dui:
        citas_activas = citas_activas.filter(mecanico__dui=mecanico_dui)

    # Servicios más solicitados: líneas de ServicioCita de las citas activas.
    servicios_top = list(
        ServicioCita.objects.filter(cita__in=citas_activas)
        .values('servicio__id', 'servicio__nombre')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad', 'servicio__nombre')
    )

    # Mecánico con más servicios: citas activas con mecánico asignado.
    mecanicos_top = list(
        citas_activas.exclude(mecanico__isnull=True)
        .values('mecanico__dui', 'mecanico__nombre', 'mecanico__apellido')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad', 'mecanico__apellido')
    )

    # Ingresos: solo citas completadas, dentro de los filtros aplicados.
    completadas = citas_activas.filter(estado=Cita.ESTADO_COMPLETADA)
    ingresos_totales = Decimal('0.00')
    for cita in completadas.prefetch_related(
        'serviciocita_set__servicio',
        'repuestos_usados__producto',
    ):
        detalle = calcular_detalle_cita(cita)
        monto = detalle['total']
        if monto is None:
            monto = detalle['total_referencia']
        if monto:
            ingresos_totales += monto

    return {
        'total_citas': citas_activas.count(),
        'servicios_completados': completadas.count(),
        'ingresos_totales': ingresos_totales,
        'servicios_top': servicios_top,
        'mecanicos_top': mecanicos_top,
    }
