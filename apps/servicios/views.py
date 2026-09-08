"""Vistas de la app servicios."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Servicio


@login_required(login_url='usuarios:login')
def catalogo_servicios(request):
    """Lista, crea y edita servicios del catálogo (SCRUM-39)."""
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    busqueda = request.GET.get('q', '').strip()
    servicios = Servicio.objects.all()
    if busqueda:
        servicios = servicios.filter(nombre__icontains=busqueda)

    servicio_editar = None
    editar_id = request.GET.get('editar')
    if editar_id:
        servicio_editar = get_object_or_404(Servicio, id=editar_id)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'guardar':
            errores = {}
            servicio_id = request.POST.get('servicio_id')
            datos = {
                'nombre':            request.POST.get('nombre', '').strip(),
                'descripcion':       request.POST.get('descripcion', '').strip(),
                'precio_base':       request.POST.get('precio_base', '').strip(),
                'duracion_estimada': request.POST.get('duracion_estimada', '').strip(),
            }

            if not datos['nombre']:
                errores['nombre'] = 'El nombre es obligatorio.'

            try:
                precio = float(datos['precio_base'])
                if precio < 0:
                    errores['precio_base'] = 'El precio no puede ser negativo.'
            except ValueError:
                errores['precio_base'] = 'Ingresá un precio válido.'

            try:
                duracion = int(datos['duracion_estimada'])
                if duracion <= 0:
                    errores['duracion_estimada'] = 'La duración debe ser mayor a 0.'
            except ValueError:
                errores['duracion_estimada'] = 'Ingresá una duración válida en minutos.'

            if errores:
                return render(request, 'servicios/catalogo_servicios.html', {
                    'servicios': servicios,
                    'errores': errores,
                    'datos': datos,
                    'busqueda': busqueda,
                    'servicio_editar': servicio_editar,
                })

            if servicio_id:
                servicio = get_object_or_404(Servicio, id=servicio_id)
                servicio.nombre = datos['nombre']
                servicio.descripcion = datos['descripcion']
                servicio.precio_base = precio
                servicio.duracion_estimada = duracion
                servicio.save()
                messages.success(request, f'Servicio "{servicio.nombre}" actualizado.')
            else:
                servicio = Servicio.objects.create(
                    nombre=datos['nombre'],
                    descripcion=datos['descripcion'],
                    precio_base=precio,
                    duracion_estimada=duracion,
                )
                messages.success(request, f'Servicio "{servicio.nombre}" creado.')

            return redirect('servicios:catalogo')

        elif accion == 'desactivar':
            servicio_id = request.POST.get('servicio_id')
            servicio = get_object_or_404(Servicio, id=servicio_id)
            servicio.activo = False
            servicio.save()
            messages.success(request, f'Servicio "{servicio.nombre}" desactivado.')
            return redirect('servicios:catalogo')

        elif accion == 'activar':
            servicio_id = request.POST.get('servicio_id')
            servicio = get_object_or_404(Servicio, id=servicio_id)
            servicio.activo = True
            servicio.save()
            messages.success(request, f'Servicio "{servicio.nombre}" activado.')
            return redirect('servicios:catalogo')

    return render(request, 'servicios/catalogo_servicios.html', {
        'servicios': servicios,
        'errores': {},
        'datos': {},
        'busqueda': busqueda,
        'servicio_editar': servicio_editar,
    })
