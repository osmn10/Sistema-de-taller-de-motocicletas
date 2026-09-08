"""Vistas de la app core."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


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
