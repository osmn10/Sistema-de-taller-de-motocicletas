"""Vistas de la app core."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def home(request):
    """Página de inicio pública (no requiere login)."""
    return render(request, 'core/home.html')


# @login_required obliga al usuario a estar autenticado. Si no lo está,
# Django lo manda al login (le paso el nombre con namespace).
@login_required(login_url='usuarios:login')
def admin_panel(request):
    """Panel principal del administrador (las 6 tarjetas)."""
    return render(request, 'core/admin_panel.html')


@login_required(login_url='usuarios:login')
def panel_mecanico(request):
    """Panel principal del mecánico (placeholder por ahora)."""
    return render(request, 'core/panel_mecanico.html')
