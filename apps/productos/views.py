"""Vistas de la app productos."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required(login_url='usuarios:login')
def inventario(request):
    """Inventario de productos y repuestos."""
    return render(request, 'productos/inventario.html')
