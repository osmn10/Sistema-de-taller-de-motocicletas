"""Vistas de la app citas."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required(login_url='usuarios:login')
def mis_citas(request):
    """Lista las citas del cliente logueado."""
    return render(request, 'citas/mis_citas.html')


@login_required(login_url='usuarios:login')
def mis_citas_mecanico(request):
    """Citas asignadas al mecánico logueado."""
    return render(request, 'citas/mis_citas_mecanico.html')


@login_required(login_url='usuarios:login')
def calendario(request):
    """Calendario de citas (vista admin)."""
    return render(request, 'citas/calendario.html')


@login_required(login_url='usuarios:login')
def agendar_cita(request):
    """Formulario para agendar una nueva cita."""
    return render(request, 'citas/agendar_cita.html')


@login_required(login_url='usuarios:login')
def cita_detalle(request, cita_id):
    """Detalle de una cita específica."""
    return render(request, 'citas/cita_detalle.html', {'cita_id': cita_id})
