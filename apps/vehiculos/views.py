"""Vistas de la app vehiculos."""
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Motocicleta, placa_validator


@login_required(login_url='usuarios:login')
def mis_motos(request):
    if not request.user.is_cliente:
        messages.error(request, 'Solo los clientes pueden acceder a esta sección.')
        return redirect('core:home')

    motos = Motocicleta.objects.filter(cliente=request.user.cliente).order_by('-activo', '-fecha_registro')

    return render(request, 'vehiculos/mis_motos.html', {
        'motos': motos,
        'total': motos.count(),
    })


@login_required(login_url='usuarios:login')
def moto_crear(request):
    if not request.user.is_cliente:
        messages.error(request, 'Solo los clientes pueden registrar motos.')
        return redirect('core:home')

    anio_max = datetime.date.today().year + 1

    if request.method == 'POST':
        errores = {}
        datos = {
            'placa':       request.POST.get('placa', '').strip().upper(),
            'marca':       request.POST.get('marca', '').strip(),
            'modelo':      request.POST.get('modelo', '').strip(),
            'anio':        request.POST.get('anio', '').strip(),
            'color':       request.POST.get('color', '').strip(),
            'kilometraje': request.POST.get('kilometraje', '').strip(),
        }

        try:
            placa_validator(datos['placa'])
        except Exception:
            errores['placa'] = 'Formato inválido. Debe ser M-#### (ej. M-1234).'
        if datos['placa'] and Motocicleta.objects.filter(placa=datos['placa']).exists():
            errores['placa'] = 'Ya existe una moto con esa placa.'

        if not datos['marca']:
            errores['marca'] = 'La marca es obligatoria.'
        if not datos['modelo']:
            errores['modelo'] = 'El modelo es obligatorio.'
        if not datos['color']:
            errores['color'] = 'El color es obligatorio.'

        try:
            anio_int = int(datos['anio'])
            if anio_int < 1980 or anio_int > anio_max:
                errores['anio'] = f'El año debe estar entre 1980 y {anio_max}.'
        except ValueError:
            anio_int = None
            errores['anio'] = 'El año debe ser un número.'

        try:
            km_int = int(datos['kilometraje'])
            if km_int < 0:
                errores['kilometraje'] = 'El kilometraje no puede ser negativo.'
        except ValueError:
            km_int = None
            errores['kilometraje'] = 'El kilometraje debe ser un número.'

        if errores:
            return render(request, 'vehiculos/motos_form.html', {
                'datos': datos,
                'errores': errores,
                'es_edicion': False,
                'anio_max': anio_max,
            })

        Motocicleta.objects.create(
            placa=datos['placa'],
            cliente=request.user.cliente,
            marca=datos['marca'],
            modelo=datos['modelo'],
            anio=anio_int,
            color=datos['color'],
            kilometraje=km_int,
        )
        messages.success(request, f'Moto {datos["placa"]} registrada correctamente.')
        return redirect('vehiculos:mis_motos')

    return render(request, 'vehiculos/motos_form.html', {
        'datos': {},
        'errores': {},
        'es_edicion': False,
        'anio_max': anio_max,
    })


@login_required(login_url='usuarios:login')
def moto_editar(request, placa):
    if not request.user.is_cliente:
        messages.error(request, 'Solo los clientes pueden editar motos.')
        return redirect('core:home')

    moto = get_object_or_404(Motocicleta, placa=placa, cliente=request.user.cliente)
    anio_max = datetime.date.today().year + 1

    if request.method == 'POST':
        errores = {}
        datos = {
            'placa':       moto.placa,
            'marca':       request.POST.get('marca', '').strip(),
            'modelo':      request.POST.get('modelo', '').strip(),
            'anio':        request.POST.get('anio', '').strip(),
            'color':       request.POST.get('color', '').strip(),
            'kilometraje': request.POST.get('kilometraje', '').strip(),
        }

        if not datos['marca']:
            errores['marca'] = 'La marca es obligatoria.'
        if not datos['modelo']:
            errores['modelo'] = 'El modelo es obligatorio.'
        if not datos['color']:
            errores['color'] = 'El color es obligatorio.'

        try:
            anio_int = int(datos['anio'])
            if anio_int < 1980 or anio_int > anio_max:
                errores['anio'] = f'El año debe estar entre 1980 y {anio_max}.'
        except ValueError:
            anio_int = None
            errores['anio'] = 'El año debe ser un número.'

        try:
            km_int = int(datos['kilometraje'])
            if km_int < 0:
                errores['kilometraje'] = 'El kilometraje no puede ser negativo.'
        except ValueError:
            km_int = None
            errores['kilometraje'] = 'El kilometraje debe ser un número.'

        if errores:
            return render(request, 'vehiculos/motos_form.html', {
                'moto': moto,
                'datos': datos,
                'errores': errores,
                'es_edicion': True,
                'anio_max': anio_max,
            })

        moto.marca = datos['marca']
        moto.modelo = datos['modelo']
        moto.anio = anio_int
        moto.color = datos['color']
        moto.kilometraje = km_int
        moto.save()
        messages.success(request, f'Moto {moto.placa} actualizada correctamente.')
        return redirect('vehiculos:mis_motos')

    return render(request, 'vehiculos/motos_form.html', {
        'moto': moto,
        'datos': {
            'placa':       moto.placa,
            'marca':       moto.marca,
            'modelo':      moto.modelo,
            'anio':        str(moto.anio),
            'color':       moto.color,
            'kilometraje': str(moto.kilometraje),
        },
        'errores': {},
        'es_edicion': True,
        'anio_max': anio_max,
    })


@login_required(login_url='usuarios:login')
def moto_toggle(request, placa):
    if not request.user.is_cliente:
        return redirect('core:home')

    if request.method != 'POST':
        return redirect('vehiculos:mis_motos')

    moto = get_object_or_404(Motocicleta, placa=placa, cliente=request.user.cliente)
    moto.activo = not moto.activo
    moto.save()
    estado = 'activada' if moto.activo else 'desactivada'
    messages.success(request, f'Moto {moto.placa} {estado}.')
    return redirect('vehiculos:mis_motos')
