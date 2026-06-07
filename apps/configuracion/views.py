"""Vistas de la app configuracion."""
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import HorarioTaller


@login_required(login_url='usuarios:login')
def horario(request):
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    for valor, _ in HorarioTaller.DIAS_SEMANA:
        HorarioTaller.objects.get_or_create(dia_semana=valor)

    if request.method == 'POST':
        errores = {}
        datos = {}

        for valor, nombre in HorarioTaller.DIAS_SEMANA:
            abierto  = request.POST.get(f'abierto_{valor}') == 'on'
            apertura = request.POST.get(f'apertura_{valor}', '').strip()
            cierre   = request.POST.get(f'cierre_{valor}', '').strip()

            datos[valor] = {'abierto': abierto, 'apertura': apertura, 'cierre': cierre}

            if abierto:
                if not apertura or not cierre:
                    errores[valor] = 'Indicá hora de apertura y cierre.'
                elif cierre <= apertura:
                    errores[valor] = 'La hora de cierre debe ser posterior a la de apertura.'

        if errores:
            horarios = [{
                'dia':      valor,
                'nombre':   nombre,
                'abierto':  datos[valor]['abierto'],
                'apertura': datos[valor]['apertura'],
                'cierre':   datos[valor]['cierre'],
                'error':    errores.get(valor, ''),
            } for valor, nombre in HorarioTaller.DIAS_SEMANA]
            return render(request, 'configuracion/horario.html', {'horarios': horarios})

        for valor, nombre in HorarioTaller.DIAS_SEMANA:
            h = HorarioTaller.objects.get(dia_semana=valor)
            h.abierto = datos[valor]['abierto']
            if h.abierto:
                h.hora_apertura = datetime.strptime(datos[valor]['apertura'], '%H:%M').time()
                h.hora_cierre   = datetime.strptime(datos[valor]['cierre'], '%H:%M').time()
            else:
                h.hora_apertura = None
                h.hora_cierre   = None
            h.save()

        messages.success(request, 'Horario de atención actualizado correctamente.')
        return redirect('configuracion:horario')

    horarios = [{
        'dia':      h.dia_semana,
        'nombre':   h.get_dia_semana_display(),
        'abierto':  h.abierto,
        'apertura': h.hora_apertura.strftime('%H:%M') if h.hora_apertura else '',
        'cierre':   h.hora_cierre.strftime('%H:%M') if h.hora_cierre else '',
        'error':    '',
    } for h in HorarioTaller.objects.all().order_by('dia_semana')]

    return render(request, 'configuracion/horario.html', {'horarios': horarios})