"""Vistas de la app usuarios."""

import re

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

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
        return redirect('usuarios:login')
    return render(request, 'usuarios/registro_cliente.html', {'errores': {}, 'datos': {}})


class LoginView(View):
    """Vista de login. Acepta DUI o email en el campo `identifier`."""

    def get(self, request):
        if request.user.is_authenticated:
            return self.redirect_by_role(request.user)
        return render(request, 'usuarios/login.html')

    def post(self, request):
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')

        if not identifier or not password:
            return render(request, 'usuarios/login.html', {
                'error': 'Por favor, complete todos los campos.'
            })

        user = authenticate(request, username=identifier, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'¡Bienvenido {user.nombre_completo}!')
            return self.redirect_by_role(user)
        else:
            return render(request, 'usuarios/login.html', {
                'error': 'DUI/Email o contraseña incorrectos.'
            })

    def redirect_by_role(self, user):
        if user.is_admin:
            return redirect('core:admin_panel')
        if user.is_mecanico:
            return redirect('core:panel_mecanico')
        return redirect('citas:mis_citas')


class LogoutView(View):
    """Cierra la sesión del usuario."""

    def get(self, request):
        logout(request)
        messages.info(request, 'Has cerrado sesión correctamente.')
        return redirect('usuarios:login')


@login_required(login_url='usuarios:login')
def mi_perfil(request):
    """
    Permite al usuario ver y editar su perfil.
    El DUI no se puede cambiar (es la llave primaria).
    Opcionalmente puede cambiar su contraseña.
    """
    # Obtener el usuario logueado
    user = request.user

    if request.method == 'POST':
        # Obtener datos del formulario
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        email = request.POST.get('email', '').strip()
        # Campos de contraseña (opcionales)
        password_actual = request.POST.get('password_actual', '').strip()
        password_nueva = request.POST.get('password_nueva', '').strip()

        # Diccionario para acumular errores
        errores = {}

        # Validar campos obligatorios
        if not nombre:
            errores['nombre'] = 'El nombre es obligatorio.'
        if not apellido:
            errores['apellido'] = 'El apellido es obligatorio.'
        if not telefono:
            errores['telefono'] = 'El teléfono es obligatorio.'
        else:
            # Validar formato del teléfono usando el validador del modelo
            try:
                telefono_validator(telefono)
            except Exception:
                errores['telefono'] = 'Formato inválido. Debe ser 0000-0000.'
        if not email:
            errores['email'] = 'El correo es obligatorio.'
        elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            errores['email'] = 'Correo electrónico inválido.'

        # Validar que el email no esté en uso por otro usuario
        if email and email != user.email:
            if Cliente.objects.filter(email=email).exclude(dui=user.dui).exists():
                errores['email'] = 'Este correo ya está en uso por otro usuario.'

        # Validar contraseña (solo si el usuario quiere cambiarla)
        if password_actual or password_nueva:
            if not password_actual:
                errores['password_actual'] = 'Debés ingresar tu contraseña actual.'
            elif not password_nueva:
                errores['password_nueva'] = 'Debés ingresar la nueva contraseña.'
            elif not user.check_password(password_actual):
                # Verificar que la contraseña actual sea correcta
                errores['password_actual'] = 'La contraseña actual es incorrecta.'
            elif len(password_nueva) < 8:
                errores['password_nueva'] = 'La nueva contraseña debe tener al menos 8 caracteres.'

        # Obtener dirección si es cliente
        direccion = ''
        if user.is_cliente:
            direccion = request.POST.get('direccion', '').strip()

        # Si hay errores, volver a mostrar el formulario
        if errores:
            return render(request, 'usuarios/mi_perfil.html', {
                'errores': errores,
                'form_nombre': nombre,
                'form_apellido': apellido,
                'form_telefono': telefono,
                'form_email': email,
                'form_direccion': direccion,
            })

    # Guardar los cambios según el tipo de usuario
        if user.is_cliente:
            # Si es cliente, actualizar TODO en el objeto cliente
            # (porque cliente hereda de usuario y tiene todos los campos)
            cliente = user.cliente
            cliente.nombre = nombre
            cliente.apellido = apellido
            cliente.telefono = telefono
            cliente.email = email
            cliente.direccion = direccion
            cliente.save()
        else:
            # Si no es cliente (mecánico o admin), guardar en usuario directamente
            user.nombre = nombre
            user.apellido = apellido
            user.telefono = telefono
            user.email = email
            user.save()

        # Si quiere cambiar contraseña, actualizarla
        if password_actual and password_nueva:
            # set_password hashea la contraseña antes de guardarla
            user.set_password(password_nueva)
            user.save()
            # Re-autenticar para que no se cierre la sesión al cambiar contraseña
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)

        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('usuarios:mi_perfil')

    # GET: mostrar formulario con datos actuales del usuario
    direccion = ''
    if user.is_cliente:
        direccion = user.cliente.direccion

    return render(request, 'usuarios/mi_perfil.html', {
        'form_nombre': user.nombre,
        'form_apellido': user.apellido,
        'form_telefono': user.telefono,
        'form_email': user.email,
        'form_direccion': direccion,
    })


@login_required(login_url='usuarios:login')
def usuarios_lista(request):
    return render(request, 'usuarios/usuarios_lista.html')


@login_required(login_url='usuarios:login')
def clientes_lista(request):
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    q = request.GET.get('q', '').strip()
    clientes = Cliente.objects.all().order_by('apellido', 'nombre')
    if q:
        clientes = clientes.filter(
            Q(dui__icontains=q) |
            Q(nombre__icontains=q) |
            Q(apellido__icontains=q) |
            Q(email__icontains=q)
        )

    return render(request, 'usuarios/clientes_lista.html', {
        'clientes': clientes,
        'q': q,
        'total': clientes.count(),
    })


@login_required(login_url='usuarios:login')
def cliente_detalle(request, dui):
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    cliente = get_object_or_404(Cliente, dui=dui)
    motos = cliente.motocicletas.all().order_by('-activo', '-fecha_registro')

    return render(request, 'usuarios/cliente_detalle.html', {
        'cliente': cliente,
        'motos': motos,
    })


@login_required(login_url='usuarios:login')
def cliente_editar(request, dui):
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    cliente = get_object_or_404(Cliente, dui=dui)

    if request.method == 'POST':
        errores = {}
        datos = {
            'nombre':    request.POST.get('nombre', '').strip(),
            'apellido':  request.POST.get('apellido', '').strip(),
            'telefono':  request.POST.get('telefono', '').strip(),
            'email':     request.POST.get('email', '').strip(),
            'direccion': request.POST.get('direccion', '').strip(),
        }

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

        if Cliente.objects.filter(email=datos['email']).exclude(dui=dui).exists():
            errores['email'] = 'Ya existe otro cliente con ese correo.'

        if errores:
            return render(request, 'usuarios/cliente_editar.html', {
                'cliente': cliente,
                'datos': datos,
                'errores': errores,
            })

        cliente.nombre = datos['nombre']
        cliente.apellido = datos['apellido']
        cliente.telefono = datos['telefono']
        cliente.email = datos['email']
        cliente.direccion = datos['direccion']
        cliente.save()
        messages.success(request, f'Cliente {cliente.nombre_completo} actualizado correctamente.')
        return redirect('usuarios:cliente_detalle', dui=cliente.dui)

    return render(request, 'usuarios/cliente_editar.html', {
        'cliente': cliente,
        'errores': {},
        'datos': {
            'nombre':    cliente.nombre,
            'apellido':  cliente.apellido,
            'telefono':  cliente.telefono,
            'email':     cliente.email,
            'direccion': cliente.direccion,
        },
    })


@login_required(login_url='usuarios:login')
def cliente_toggle(request, dui):
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    if request.method != 'POST':
        return redirect('usuarios:cliente_detalle', dui=dui)

    cliente = get_object_or_404(Cliente, dui=dui)
    cliente.activo = not cliente.activo
    cliente.save()
    estado = 'activado' if cliente.activo else 'desactivado'
    messages.success(request, f'Cliente {cliente.nombre_completo} {estado}.')
    return redirect('usuarios:cliente_detalle', dui=cliente.dui)