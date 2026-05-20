"""Vistas de la app usuarios."""

import re

from django.contrib import messages
from django.shortcuts import redirect, render

from .models import Cliente, dui_validator, telefono_validator


def registro_cliente(request):
    """Muestra y procesa el formulario de registro de un nuevo cliente (RF-01)."""

    if request.method == 'POST':
        errores = {}
        datos = {
            'dui':       request.POST.get('dui', '').strip(),
            'nombre':    request.POST.get('nombre', '').strip(),
            'apellido':  request.POST.get('apellido', '').strip(),
            'telefono':  request.POST.get('telefono', '').strip(),
            'email':     request.POST.get('email', '').strip(),
            'direccion': request.POST.get('direccion', '').strip(),
        }
        contrasena = request.POST.get('contrasena', '')
        confirmar  = request.POST.get('confirmar', '')

        # Validaciones
        try:
            dui_validator(datos['dui'])
        except Exception:
            errores['dui'] = 'Formato inválido. Debe ser 00000000-0.'

        if not datos['nombre']:
            errores['nombre'] = 'El nombre es obligatorio.'

        if not datos['apellido']:
            errores['apellido'] = 'El apellido es obligatorio.'

        try:
            telefono_validator(datos['telefono'])
        except Exception:
            errores['telefono'] = 'Formato inválido. Debe ser 0000-0000.'

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', datos['email']):
            errores['email'] = 'Correo electrónico inválido.'

        if not datos['direccion']:
            errores['direccion'] = 'La dirección es obligatoria.'

        if len(contrasena) < 8:
            errores['contrasena'] = 'La contraseña debe tener al menos 8 caracteres.'
        elif contrasena != confirmar:
            errores['confirmar'] = 'Las contraseñas no coinciden.'

        if Cliente.objects.filter(dui=datos['dui']).exists():
            errores['dui'] = 'Ya existe una cuenta con ese DUI.'

        if Cliente.objects.filter(email=datos['email']).exists():
            errores['email'] = 'Ya existe una cuenta con ese correo.'

        if errores:
            return render(request, 'usuarios/registro_cliente.html', {
                'errores': errores,
                'datos': datos,
            })

        # Crear cliente
        cliente = Cliente(
            dui=datos['dui'],
            nombre=datos['nombre'],
            apellido=datos['apellido'],
            telefono=datos['telefono'],
            email=datos['email'],
            direccion=datos['direccion'],
        )
        cliente.set_password(contrasena)
        cliente.save()

        messages.success(request, 'Cuenta creada correctamente. Ya podés iniciar sesión.')
        return redirect('usuarios:registro_cliente')

    return render(request, 'usuarios/registro_cliente.html', {'errores': {}, 'datos': {}})
