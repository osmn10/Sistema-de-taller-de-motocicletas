"""Vistas de la app core."""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.citas.models import Cita, EstadoCita, ServicioCita
from apps.citas.totales import calcular_detalle_cita
from apps.productos.models import Producto
from apps.usuarios.models import Cliente

TIPOS_ACTIVOS = [EstadoCita.TIPO_INICIO, EstadoCita.TIPO_PROCESO]


def home(request):
    """Página de inicio pública. Si ya hay sesión, redirige al panel del rol."""
    if request.user.is_authenticated:
        if request.user.is_admin:
            return redirect('core:admin_panel')
        if request.user.is_mecanico:
            return redirect('core:panel_mecanico')
        return redirect('citas:mis_citas')
    return render(request, 'core/home.html')


@login_required(login_url='usuarios:login')
def admin_panel(request):
    """Panel principal del administrador con indicadores del día."""
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    hoy = timezone.localdate()
    citas_activas = Cita.objects.filter(estado__tipo__in=TIPOS_ACTIVOS)
    contexto = {
        'hoy': hoy,
        'citas_hoy': citas_activas.filter(fecha=hoy).count(),
        'citas_pendientes': Cita.objects.filter(estado__tipo=EstadoCita.TIPO_INICIO).count(),
        'estado_inicial': EstadoCita.objects.filter(tipo=EstadoCita.TIPO_INICIO).first(),
        'clientes_activos': Cliente.objects.filter(activo=True).count(),
        'productos_stock_bajo': sum(1 for p in Producto.objects.filter(activo=True) if p.stock_bajo),
        'proximas_citas': (
            citas_activas.filter(fecha__gte=hoy)
            .select_related('cliente', 'motocicleta', 'mecanico', 'estado')
            .order_by('fecha', 'hora')[:6]
        ),
    }
    return render(request, 'core/admin_panel.html', contexto)


@login_required(login_url='usuarios:login')
def panel_mecanico(request):
    """Panel principal del mecánico con su carga de trabajo."""
    if not request.user.is_mecanico:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    hoy = timezone.localdate()
    mis_citas = Cita.objects.filter(mecanico=request.user.mecanico, estado__tipo__in=TIPOS_ACTIVOS)
    contexto = {
        'hoy': hoy,
        'citas_hoy': mis_citas.filter(fecha=hoy).count(),
        'citas_en_proceso': mis_citas.filter(estado__tipo=EstadoCita.TIPO_PROCESO).count(),
        'citas_semana': mis_citas.filter(fecha__gte=hoy, fecha__lte=hoy + timedelta(days=7)).count(),
        'sin_asignar': Cita.objects.filter(mecanico__isnull=True, estado__tipo__in=TIPOS_ACTIVOS, fecha__gte=hoy).count(),
        'proximas_citas': (
            mis_citas.filter(fecha__gte=hoy)
            .select_related('cliente', 'motocicleta', 'estado')
            .order_by('fecha', 'hora')[:6]
        ),
    }
    return render(request, 'core/panel_mecanico.html', contexto)


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
    estados = list(EstadoCita.objects.all())
    conteo_estado = {estado.codigo: 0 for estado in estados}
    for fila in citas_periodo.values('estado').annotate(n=Count('id')):
        conteo_estado[fila['estado']] = fila['n']

    completadas = citas_periodo.filter(estado__tipo=EstadoCita.TIPO_COMPLETADO)

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
            {'etiqueta': estado.nombre, 'valor': conteo_estado[estado.codigo]}
            for estado in estados
        ],
        'servicios_completados': servicios_completados,
        'ingresos_periodo': ingresos,
        'total_productos': total_productos,
        'productos_en_nivel': productos_en_nivel,
        'avance_inventario': avance_inventario,
        'productos_bajos': productos_bajos,
    }
    return render(request, 'core/dashboard.html', contexto)
