"""Vistas de la app vehiculos."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required(login_url='usuarios:login')
def mis_motos(request):
    """Lista las motocicletas del cliente logueado."""
    return render(request, 'vehiculos/mis_motos.html')


@login_required(login_url='usuarios:login')
def motos_form(request):
    """Formulario para registrar o editar una motocicleta."""
    return render(request, 'vehiculos/motos_form.html')
