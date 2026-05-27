
"""Vistas de la app usuarios."""
import re
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q  # Q permite hacer filtros con OR en la BD
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .models import Cliente, dui_validator, telefono_validator


# login_required redirige al login si el usuario no está autenticado.
# El parámetro login_url indica a dónde ir (usando el namespace de la app).
@login_required(login_url='usuarios:login')
def mi_perfil(request):
    """Perfil del usuario logueado (lo termina SCRUM-43)."""
    return render(request, 'usuarios/mi_perfil.html')


@login_required(login_url='usuarios:login')
def usuarios_lista(request):
    """Gestión de usuarios del sistema: admins y mecánicos."""
    return render(request, 'usuarios/usuarios_lista.html')


# ---------------------------------------------------------------------------
# SCRUM-29 · Gestionar clientes (admin)
# ---------------------------------------------------------------------------

@login_required(login_url='usuarios:login')
def clientes_lista(request):
    # Solo los admin pueden entrar acá. Si no lo es, lo mando al inicio
    # con un mensaje de error.
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    # Si vino una búsqueda por ?q=... la guardo. Si no, queda vacío.
    q = request.GET.get('q', '').strip()

    # Traigo todos los clientes ordenados por apellido y nombre.
    clientes = Cliente.objects.all().order_by('apellido', 'nombre')

    # Si hay búsqueda, filtro por DUI, nombre, apellido o correo.
    # icontains = "contiene" sin distinguir mayúsculas/minúsculas.
    # Q(...) | Q(...) significa OR (cualquiera de los campos puede coincidir).
    if q:
        clientes = clientes.filter(
            Q(dui__icontains=q) |
            Q(nombre__icontains=q) |
            Q(apellido__icontains=q) |
            Q(email__icontains=q)
        )

    # render arma la respuesta HTML usando el template + el diccionario de contexto.
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

    # get_object_or_404 trae el cliente con ese DUI o devuelve un 404
    # si no existe. Mucho más limpio que un try/except con DoesNotExist.
    cliente = get_object_or_404(Cliente, dui=dui)
    return render(request, 'usuarios/cliente_detalle.html', {'cliente': cliente})


@login_required(login_url='usuarios:login')
def cliente_editar(request, dui):
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    cliente = get_object_or_404(Cliente, dui=dui)

    # Si el método es POST significa que el usuario envió el formulario.
    # Si es GET, solo tengo que mostrar el form con los datos actuales del cliente.
    if request.method == 'POST':
        errores = {}

        # Saco cada campo del POST y le hago strip() para limpiar espacios.
        datos = {
            'nombre':    request.POST.get('nombre', '').strip(),
            'apellido':  request.POST.get('apellido', '').strip(),
            'telefono':  request.POST.get('telefono', '').strip(),
            'email':     request.POST.get('email', '').strip(),
            'direccion': request.POST.get('direccion', '').strip(),
        }

        # Valido cada campo. Si algo está mal, agrego el error al diccionario.
        if not datos['nombre']:
            errores['nombre'] = 'El nombre es obligatorio.'
        if not datos['apellido']:
            errores['apellido'] = 'El apellido es obligatorio.'

        # El validator de teléfono está definido en models.py con un regex.
        # Si no cumple el formato, tira ValidationError, lo agarro y guardo el error.
        try:
            telefono_validator(datos['telefono'])
        except Exception:
            errores['telefono'] = 'Formato inválido. Debe ser 0000-0000.'

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', datos['email']):
            errores['email'] = 'Correo electrónico inválido.'
        if not datos['direccion']:
            errores['direccion'] = 'La dirección es obligatoria.'

        # El correo es único en la BD. Verifico que no exista en OTRO cliente
        # (exclude(dui=dui) descarta al cliente que estoy editando).
        if Cliente.objects.filter(email=datos['email']).exclude(dui=dui).exists():
            errores['email'] = 'Ya existe otro cliente con ese correo.'

        # Si hubo errores, vuelvo a mostrar el form con los datos que ingresó
        # el usuario (así no se le pierde lo que escribió) y los mensajes de error.
        if errores:
            return render(request, 'usuarios/cliente_editar.html', {
                'cliente': cliente,
                'datos': datos,
                'errores': errores,
            })

        # Si llegamos acá, todo está OK. Actualizo el cliente y lo guardo.
        cliente.nombre = datos['nombre']
        cliente.apellido = datos['apellido']
        cliente.telefono = datos['telefono']
        cliente.email = datos['email']
        cliente.direccion = datos['direccion']
        cliente.save()
        messages.success(request, f'Cliente {cliente.nombre_completo} actualizado correctamente.')
        # redirect manda al detalle del cliente con su DUI.
        return redirect('usuarios:cliente_detalle', dui=cliente.dui)

    # Si fue GET, muestro el form precargado con los datos actuales del cliente.
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
    """Activa o desactiva un cliente (soft delete con el campo `activo`)."""
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    # Solo acepto POST para esta acción (es una operación que modifica datos,
    # no debería poder hacerse con un GET desde un link directo).
    if request.method != 'POST':
        return redirect('usuarios:cliente_detalle', dui=dui)

    cliente = get_object_or_404(Cliente, dui=dui)
    # Invierto el estado: si estaba activo, queda inactivo y viceversa.
    cliente.activo = not cliente.activo
    cliente.save()
    estado = 'activado' if cliente.activo else 'desactivado'
    messages.success(request, f'Cliente {cliente.nombre_completo} {estado}.')
    return redirect('usuarios:cliente_detalle', dui=cliente.dui)


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
    """
    Vista de login. Es una Class-Based View porque separa fácil el GET (mostrar
    el form) del POST (procesarlo). Hace lo mismo que dos funciones get/post pero
    agrupadas.
    """

    def get(self, request):
        # Si ya está logueado, lo mando directo a su panel según el rol.
        if request.user.is_authenticated:
            return self.redirect_by_role(request.user)
        return render(request, 'usuarios/login.html')

    def post(self, request):
        # El campo "identifier" acepta tanto DUI como email (lo resuelve
        # el backend custom en backends.py).
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')

        if not identifier or not password:
            return render(request, 'usuarios/login.html', {
                'error': 'Por favor, complete todos los campos.'
            })

        # authenticate() devuelve el usuario si las credenciales son válidas,
        # o None si no. Internamente prueba con todos los AUTH_BACKENDS configurados.
        user = authenticate(request, username=identifier, password=password)

        if user is not None:
            # login() guarda el usuario en la sesión.
            login(request, user)
            messages.success(request, f'¡Bienvenido {user.nombre_completo}!')
            return self.redirect_by_role(user)
        else:
            return render(request, 'usuarios/login.html', {
                'error': 'DUI/Email o contraseña incorrectos.'
            })

    def redirect_by_role(self, user):
        # Cada rol tiene su propio "home" después de loguearse.
        if user.is_admin:
            return redirect('core:admin_panel')
        if user.is_mecanico:
            return redirect('core:panel_mecanico')
        return redirect('citas:mis_citas')


class LogoutView(View):
    """Vista para cerrar la sesión del usuario."""

    def get(self, request):
        logout(request)
        messages.info(request, 'Has cerrado sesión correctamente.')
        return redirect('usuarios:login')