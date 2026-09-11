"""Vistas de la app core."""

from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render

from apps.citas.models import Cita, ServicioCita
from apps.citas.totales import calcular_detalle_cita
from apps.productos.models import Producto


def home(request):
    """Página de inicio pública."""
    return render(request, 'core/home.html')


@login_required(login_url='usuarios:login')
def admin_panel(request):
    """Panel principal del administrador."""
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')
    return render(request, 'core/admin_panel.html')


@login_required(login_url='usuarios:login')
def panel_mecanico(request):
    """Panel principal del mecánico."""
    if not request.user.is_mecanico:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')
    return render(request, 'core/panel_mecanico.html')


def _rango_fechas(request):
    """Lee ?desde= y ?hasta= (YYYY-MM-DD).

    Por defecto toma desde el día 1 del mes actual hasta hoy. Si las fechas
    vienen invertidas se intercambian; si vienen mal formadas se ignoran.
    """
    hoy = date.today()

    try:
        desde_str = request.GET.get('desde', '')
        desde = date.fromisoformat(desde_str) if desde_str else hoy.replace(day=1)
    except ValueError:
        desde = hoy.replace(day=1)

    try:
        hasta_str = request.GET.get('hasta', '')
        hasta = date.fromisoformat(hasta_str) if hasta_str else hoy
    except ValueError:
        hasta = hoy

    if hasta < desde:
        desde, hasta = hasta, desde

    return desde, hasta


@login_required(login_url='usuarios:login')
def dashboard(request):
    """V2SCRUM-40. Panel de KPIs del taller y alerta de stock bajo."""
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    desde, hasta = _rango_fechas(request)
    citas_periodo = Cita.objects.filter(fecha__gte=desde, fecha__lte=hasta)

    # Conteo de citas por estado dentro del período.
    conteo_estado = {clave: 0 for clave, _ in Cita.ESTADOS}
    for fila in citas_periodo.values('estado').annotate(n=Count('id')):
        conteo_estado[fila['estado']] = fila['n']

    completadas = citas_periodo.filter(estado=Cita.ESTADO_COMPLETADA)

    servicios_completados = ServicioCita.objects.filter(cita__in=completadas).count()

    # Ingresos: suma del total de cada cita completada, reutilizando la fuente
    # económica compartida (V2SCRUM-27). Si no hay total firme se usa la
    # estimación de referencia.
    ingresos = Decimal('0.00')
    for cita in completadas.prefetch_related(
        'serviciocita_set__servicio',
        'repuestos_usados__producto',
    ):
        detalle = calcular_detalle_cita(cita)
        monto = detalle['total']
        if monto is None:
            monto = detalle['total_referencia']
        if monto:
            ingresos += monto

    productos_activos = Producto.objects.filter(activo=True)
    total_productos = productos_activos.count()
    productos_bajos = [p for p in productos_activos if p.stock_bajo]
    productos_en_nivel = total_productos - len(productos_bajos)
    avance_inventario = (
        round(productos_en_nivel / total_productos * 100) if total_productos else 100
    )

    contexto = {
        'desde': desde,
        'hasta': hasta,
        'total_citas': citas_periodo.count(),
        'por_estado': [
            {'etiqueta': etiqueta, 'valor': conteo_estado[clave]}
            for clave, etiqueta in Cita.ESTADOS
        ],
        'servicios_completados': servicios_completados,
        'ingresos_periodo': ingresos,
        'total_productos': total_productos,
        'productos_en_nivel': productos_en_nivel,
        'avance_inventario': avance_inventario,
        'productos_bajos': productos_bajos,
    }
    return render(request, 'core/dashboard.html', contexto)
