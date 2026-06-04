"""Vistas de la app citas."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Cita


@login_required(login_url='usuarios:login')
def mis_citas(request):
    citas = Cita.objects.filter(
        cliente=request.user.cliente,
    ).exclude(estado=Cita.ESTADO_CANCELADA).order_by('-fecha', '-hora')
    return render(request, 'citas/mis_citas.html', {'citas': citas})


@login_required(login_url='usuarios:login')
def cita_detalle(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, cliente=request.user.cliente)
    servicios = cita.serviciocita_set.select_related('servicio').all()
    return render(request, 'citas/cita_detalle.html', {
        'cita': cita,
        'servicios': servicios,
    })


@login_required(login_url='usuarios:login')
def cancelar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, cliente=request.user.cliente)
    if request.method == 'POST':
        if cita.puede_cancelarse():
            cita.estado = Cita.ESTADO_CANCELADA
            cita.save()
            messages.success(request, f'Cita cancelada correctamente.')
        else:
            messages.error(request, 'Esta cita no puede cancelarse.')
        return redirect('citas:mis_citas')
    return redirect('citas:cita_detalle', cita_id=cita.id)


@login_required(login_url='usuarios:login')
def calendario(request):
    return render(request, 'citas/calendario.html')


@login_required(login_url='usuarios:login')
def mis_citas_mecanico(request):
    return render(request, 'citas/mis_citas_mecanico.html')
