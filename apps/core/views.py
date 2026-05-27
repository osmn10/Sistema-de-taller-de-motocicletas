"""Vistas de la app core."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def home(request):
    """Página de inicio pública."""
    return render(request, 'core/home.html')


@login_required(login_url='usuarios:login')
def admin_panel(request):
    """Panel principal del administrador."""
    return render(request, 'core/admin_panel.html')


@login_required(login_url='usuarios:login')
def panel_mecanico(request):
    """Panel principal del mecánico."""
    return render(request, 'core/panel_mecanico.html')
