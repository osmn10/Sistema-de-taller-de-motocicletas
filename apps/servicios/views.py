"""Vistas de la app servicios."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required(login_url='usuarios:login')
def catalogo(request):
    """Catálogo de servicios del taller."""
    return render(request, 'servicios/catalogo.html')
