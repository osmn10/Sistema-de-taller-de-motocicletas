"""Vistas de la app core."""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.citas.models import Cita
from apps.productos.models import Producto
from apps.usuarios.models import Cliente

ESTADOS_ACTIVOS = [Cita.ESTADO_PENDIENTE, Cita.ESTADO_CONFIRMADA, Cita.ESTADO_EN_PROCESO]


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
    citas_activas = Cita.objects.filter(estado__in=ESTADOS_ACTIVOS)
    contexto = {
        'hoy': hoy,
        'citas_hoy': citas_activas.filter(fecha=hoy).count(),
        'citas_pendientes': Cita.objects.filter(estado=Cita.ESTADO_PENDIENTE).count(),
        'clientes_activos': Cliente.objects.filter(activo=True).count(),
        'productos_stock_bajo': sum(1 for p in Producto.objects.filter(activo=True) if p.stock_bajo),
        'proximas_citas': (
            citas_activas.filter(fecha__gte=hoy)
            .select_related('cliente', 'motocicleta', 'mecanico')
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
    mis_citas = Cita.objects.filter(mecanico=request.user.mecanico, estado__in=ESTADOS_ACTIVOS)
    contexto = {
        'hoy': hoy,
        'citas_hoy': mis_citas.filter(fecha=hoy).count(),
        'citas_en_proceso': mis_citas.filter(estado=Cita.ESTADO_EN_PROCESO).count(),
        'citas_semana': mis_citas.filter(fecha__gte=hoy, fecha__lte=hoy + timedelta(days=7)).count(),
        'sin_asignar': Cita.objects.filter(mecanico__isnull=True, estado__in=ESTADOS_ACTIVOS, fecha__gte=hoy).count(),
        'proximas_citas': (
            mis_citas.filter(fecha__gte=hoy)
            .select_related('cliente', 'motocicleta')
            .order_by('fecha', 'hora')[:6]
        ),
    }
    return render(request, 'core/panel_mecanico.html', contexto)
