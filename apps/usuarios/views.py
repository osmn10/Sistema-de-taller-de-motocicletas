"""Vistas de la app usuarios."""
import re
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import connection, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .models import Cliente, Mecanico, Usuario, dui_validator, telefono_validator

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
    user = request.user

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        email = request.POST.get('email', '').strip()
        password_actual = request.POST.get('password_actual', '').strip()
        password_nueva = request.POST.get('password_nueva', '').strip()

        errores = {}

        if not nombre:
            errores['nombre'] = 'El nombre es obligatorio.'
        if not apellido:
            errores['apellido'] = 'El apellido es obligatorio.'
        if not telefono:
            errores['telefono'] = 'El teléfono es obligatorio.'
        else:
            try:
                telefono_validator(telefono)
            except Exception:
                errores['telefono'] = 'Formato inválido. Debe ser 0000-0000.'
        if not email:
            errores['email'] = 'El correo es obligatorio.'
        elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            errores['email'] = 'Correo electrónico inválido.'

        if email and email != user.email:
            if Cliente.objects.filter(email=email).exclude(dui=user.dui).exists():
                errores['email'] = 'Este correo ya está en uso por otro usuario.'

        if password_actual or password_nueva:
            if not password_actual:
                errores['password_actual'] = 'Debés ingresar tu contraseña actual.'
            elif not password_nueva:
                errores['password_nueva'] = 'Debés ingresar la nueva contraseña.'
            elif not user.check_password(password_actual):
                errores['password_actual'] = 'La contraseña actual es incorrecta.'
            elif len(password_nueva) < 8:
                errores['password_nueva'] = 'La nueva contraseña debe tener al menos 8 caracteres.'

        direccion = ''
        if user.is_cliente:
            direccion = request.POST.get('direccion', '').strip()

        if errores:
            return render(request, 'usuarios/mi_perfil.html', {
                'errores': errores,
                'form_nombre': nombre,
                'form_apellido': apellido,
                'form_telefono': telefono,
                'form_email': email,
                'form_direccion': direccion,
            })

        if user.is_cliente:
            cliente = user.cliente
            cliente.nombre = nombre
            cliente.apellido = apellido
            cliente.telefono = telefono
            cliente.email = email
            cliente.direccion = direccion
            cliente.save()
        else:
            user.nombre = nombre
            user.apellido = apellido
            user.telefono = telefono
            user.email = email
            user.save()

        if password_actual and password_nueva:
            user.set_password(password_nueva)
            user.save()
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)

        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('usuarios:mi_perfil')

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
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    rol_filtro    = request.GET.get('rol', '').strip()
    estado_filtro = request.GET.get('estado', '').strip()

    usuarios = Usuario.objects.filter(
        Q(is_staff=True) | Q(mecanico__isnull=False)
    ).distinct().order_by('apellido', 'nombre')

    if rol_filtro == 'admin':
        usuarios = usuarios.filter(is_staff=True, mecanico__isnull=True)
    elif rol_filtro == 'mecanico':
        usuarios = usuarios.filter(mecanico__isnull=False)

    if estado_filtro == 'activo':
        usuarios = usuarios.filter(activo=True)
    elif estado_filtro == 'inactivo':
        usuarios = usuarios.filter(activo=False)

    return render(request, 'usuarios/usuarios_lista.html', {
        'usuarios':       usuarios,
        'rol_filtro':     rol_filtro,
        'estado_filtro':  estado_filtro,
        'total':          usuarios.count(),
    })

@login_required(login_url='usuarios:login')
def usuario_crear(request):
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    if request.method == 'POST':
        errores = {}
        datos = {
            'dui':         request.POST.get('dui', '').strip(),
            'nombre':      request.POST.get('nombre', '').strip(),
            'apellido':    request.POST.get('apellido', '').strip(),
            'telefono':    request.POST.get('telefono', '').strip(),
            'email':       request.POST.get('email', '').strip(),
            'rol':         request.POST.get('rol', '').strip(),
            'especialidad': request.POST.get('especialidad', '').strip(),
        }
        contrasena = request.POST.get('contrasena', '')

        try:
            dui_validator(datos['dui'])
        except Exception:
            errores['dui'] = 'Formato inválido. Debe ser 00000000-0.'

        if not errores.get('dui') and Usuario.objects.filter(dui=datos['dui']).exists():
            errores['dui'] = 'Ya existe un usuario con ese DUI.'

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
        elif Usuario.objects.filter(email=datos['email']).exists():
            errores['email'] = 'Ya existe un usuario con ese correo.'

        if datos['rol'] not in ('admin', 'mecanico'):
            errores['rol'] = 'Seleccioná un rol válido.'

        if datos['rol'] == 'mecanico' and not datos['especialidad']:
            errores['especialidad'] = 'La especialidad es obligatoria para mecánicos.'

        if len(contrasena) < 8:
            errores['contrasena'] = 'La contraseña debe tener al menos 8 caracteres.'

        if errores:
            return render(request, 'usuarios/usuario_crear.html', {
                'errores':       errores,
                'datos':         datos,
                'especialidades': Mecanico.ESPECIALIDADES,
            })

        try:
            if datos['rol'] == 'admin':
                Usuario.objects.create_admin(
                    dui=datos['dui'],
                    password=contrasena,
                    nombre=datos['nombre'],
                    apellido=datos['apellido'],
                    telefono=datos['telefono'],
                    email=datos['email'],
                )
            else:
                Usuario.objects.create_mecanico(
                    dui=datos['dui'],
                    password=contrasena,
                    especialidad=datos['especialidad'],
                    nombre=datos['nombre'],
                    apellido=datos['apellido'],
                    telefono=datos['telefono'],
                    email=datos['email'],
                )
            messages.success(request, f'Usuario {datos["nombre"]} {datos["apellido"]} creado correctamente.')
            return redirect('usuarios:usuarios_lista')
        except Exception:
            messages.error(request, 'Ocurrió un error al crear el usuario. Intentá de nuevo.')

    return render(request, 'usuarios/usuario_crear.html', {
        'errores':       {},
        'datos':         {},
        'especialidades': Mecanico.ESPECIALIDADES,
    })


@login_required(login_url='usuarios:login')
def usuario_editar(request, dui):
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    usuario = get_object_or_404(Usuario, dui=dui)

    if not (usuario.is_admin or usuario.is_mecanico):
        messages.error(request, 'Este usuario no pertenece al sistema interno.')
        return redirect('usuarios:usuarios_lista')

    if request.method == 'POST':
        errores = {}
        datos = {
            'nombre':       request.POST.get('nombre', '').strip(),
            'apellido':     request.POST.get('apellido', '').strip(),
            'telefono':     request.POST.get('telefono', '').strip(),
            'email':        request.POST.get('email', '').strip(),
            'rol':          request.POST.get('rol', '').strip(),
            'especialidad': request.POST.get('especialidad', '').strip(),
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
        elif Usuario.objects.filter(email=datos['email']).exclude(dui=dui).exists():
            errores['email'] = 'Ya existe otro usuario con ese correo.'

        if datos['rol'] not in ('admin', 'mecanico'):
            errores['rol'] = 'Seleccioná un rol válido.'

        if datos['rol'] == 'mecanico' and not datos['especialidad']:
            errores['especialidad'] = 'La especialidad es obligatoria para mecánicos.'

        if errores:
            return render(request, 'usuarios/usuario_editar.html', {
                'usuario':        usuario,
                'errores':        errores,
                'datos':          datos,
                'especialidades': Mecanico.ESPECIALIDADES,
            })

        try:
            rol_actual = 'admin' if usuario.is_admin else 'mecanico'

            usuario.nombre   = datos['nombre']
            usuario.apellido = datos['apellido']
            usuario.telefono = datos['telefono']
            usuario.email    = datos['email']

            with transaction.atomic():
                if datos['rol'] == rol_actual:
                    if datos['rol'] == 'mecanico':
                        usuario.mecanico.especialidad = datos['especialidad']
                        usuario.mecanico.save()
                    usuario.save()

                elif datos['rol'] == 'admin':
                    # Mecánico → Admin: borrar solo el subregistro, marcar is_staff
                    with connection.cursor() as cursor:
                        cursor.execute(
                            f"DELETE FROM {Mecanico._meta.db_table} WHERE usuario_ptr_id = %s",
                            [dui]
                        )
                    usuario.is_staff = True
                    usuario.save()

                else:
                    # Admin → Mecánico: quitar is_staff, insertar subregistro
                    usuario.is_staff = False
                    usuario.save()
                    with connection.cursor() as cursor:
                        cursor.execute(
                            f"INSERT INTO {Mecanico._meta.db_table} (usuario_ptr_id, especialidad) VALUES (%s, %s)",
                            [dui, datos['especialidad']]
                        )

            messages.success(request, f'Usuario {usuario.nombre_completo} actualizado correctamente.')
            return redirect('usuarios:usuarios_lista')

        except Exception:
            messages.error(request, 'Ocurrió un error al actualizar el usuario. Intentá de nuevo.')

    rol_actual         = 'admin' if usuario.is_admin else 'mecanico'
    especialidad_actual = usuario.mecanico.especialidad if usuario.is_mecanico else ''

    return render(request, 'usuarios/usuario_editar.html', {
        'usuario': usuario,
        'errores': {},
        'datos': {
            'nombre':       usuario.nombre,
            'apellido':     usuario.apellido,
            'telefono':     usuario.telefono,
            'email':        usuario.email,
            'rol':          rol_actual,
            'especialidad': especialidad_actual,
        },
        'especialidades': Mecanico.ESPECIALIDADES,
    })


@login_required(login_url='usuarios:login')
def usuario_toggle(request, dui):
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    if request.method != 'POST':
        return redirect('usuarios:usuarios_lista')

    usuario = get_object_or_404(Usuario, dui=dui)

    if not (usuario.is_admin or usuario.is_mecanico):
        messages.error(request, 'Este usuario no pertenece al sistema interno.')
        return redirect('usuarios:usuarios_lista')

    if usuario.is_admin and usuario.activo:
        admins_activos = Usuario.objects.filter(
            is_staff=True,
            activo=True,
            mecanico__isnull=True,
            cliente__isnull=True,
        ).count()
        if admins_activos <= 1:
            messages.error(request, 'No se puede desactivar al único administrador activo del sistema.')
            return redirect('usuarios:usuarios_lista')

    usuario.activo = not usuario.activo
    usuario.save()
    estado = 'activado' if usuario.activo else 'desactivado'
    messages.success(request, f'Usuario {usuario.nombre_completo} {estado}.')
    return redirect('usuarios:usuarios_lista')


@login_required(login_url='usuarios:login')
def usuario_reset_password(request, dui):
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    if request.method != 'POST':
        return redirect('usuarios:usuarios_lista')

    usuario = get_object_or_404(Usuario, dui=dui)

    if not (usuario.is_admin or usuario.is_mecanico):
        messages.error(request, 'Este usuario no pertenece al sistema interno.')
        return redirect('usuarios:usuarios_lista')

    nueva_contrasena = request.POST.get('nueva_contrasena', '').strip()

    if len(nueva_contrasena) < 8:
        messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        return redirect('usuarios:usuario_editar', dui=dui)

    usuario.set_password(nueva_contrasena)
    usuario.save()
    messages.success(request, f'Contraseña de {usuario.nombre_completo} restablecida correctamente.')
    return redirect('usuarios:usuarios_lista')

@login_required(login_url='usuarios:login')
def clientes_lista(request):
    """SCRUM-29. Tabla de clientes para el admin con búsqueda por DUI, nombre, apellido o correo."""
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    # `q` es opcional: si no viene, lista todo
    q = request.GET.get('q', '').strip()
    clientes = Cliente.objects.all().order_by('apellido', 'nombre')
    if q:
        # `icontains` = LIKE case-insensitive; Q permite combinar con OR (uno cualquiera coincide)
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
    """SCRUM-29. Vista de detalle de un cliente con sus motos asociadas (solo lectura para admin)."""
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    cliente = get_object_or_404(Cliente, dui=dui)
    # related_name='motocicletas' definido en el FK del modelo Motocicleta → cliente.motocicletas.all()
    motos = cliente.motocicletas.all().order_by('-activo', '-fecha_registro')

    return render(request, 'usuarios/cliente_detalle.html', {
        'cliente': cliente,
        'motos': motos,
    })


@login_required(login_url='usuarios:login')
def cliente_editar(request, dui):
    """SCRUM-29. Edita datos del cliente. El DUI no se toca (es PK)."""
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    cliente = get_object_or_404(Cliente, dui=dui)

    if request.method == 'POST':
        errores = {}
        # patrón del proyecto: validación manual, sin django.forms — control total del markup
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
            telefono_validator(datos['telefono'])  # ya valida formato 0000-0000
        except Exception:
            errores['telefono'] = 'Formato inválido. Debe ser 0000-0000.'
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', datos['email']):
            errores['email'] = 'Correo electrónico inválido.'
        if not datos['direccion']:
            errores['direccion'] = 'La dirección es obligatoria.'

        # excluye al propio cliente para que no se choque consigo mismo al "cambiar" al mismo correo
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
    """SCRUM-29. Soft delete del cliente. No borramos físicamente — preservamos motos e historial."""
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    # solo POST: un GET no debe poder activar/desactivar
    if request.method != 'POST':
        return redirect('usuarios:cliente_detalle', dui=dui)

    cliente = get_object_or_404(Cliente, dui=dui)
    cliente.activo = not cliente.activo
    cliente.save()
    estado = 'activado' if cliente.activo else 'desactivado'
    messages.success(request, f'Cliente {cliente.nombre_completo} {estado}.')
    return redirect('usuarios:cliente_detalle', dui=cliente.dui)
