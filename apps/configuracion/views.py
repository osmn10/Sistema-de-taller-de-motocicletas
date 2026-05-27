"""Vistas de la app configuracion."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required(login_url='usuarios:login')
def horario(request):
    """Configuración del horario del taller."""
    return render(request, 'configuracion/horario.html')
