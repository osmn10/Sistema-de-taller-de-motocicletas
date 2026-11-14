"""Vistas de la app productos — CRUD de inventario de repuestos."""

import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import Producto, Proveedor

# Formato fijo del código de producto: PROD- seguido de 4 dígitos (ej. PROD-0001)
CODIGO_PRODUCTO_REGEX = re.compile(r'^PROD-\d{4}$')


@login_required(login_url='usuarios:login')
def inventario(request):
    """
    Lista todos los productos del inventario.
    Permite buscar por código, nombre o proveedor, y filtrar solo los de stock bajo.
    Muestra alerta si hay productos con stock bajo.
    """
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    # Obtener el término de búsqueda del parámetro GET (si existe)
    busqueda = request.GET.get('q', '').strip()
    solo_stock_bajo = request.GET.get('stock_bajo') == '1'

    # Filtrar solo productos activos
    productos = Producto.objects.filter(activo=True).select_related('proveedor')

    # Si hay búsqueda, filtrar por código, nombre o proveedor
    if busqueda:
        productos = productos.filter(
            # __icontains busca texto sin importar mayúsculas/minúsculas
            Q(codigo__icontains=busqueda)
            | Q(nombre__icontains=busqueda)
            | Q(proveedor__nombre__icontains=busqueda)
        )

    # Filtro de stock bajo: compara stock_actual contra stock_minimo en la base de datos
    if solo_stock_bajo:
        productos = productos.filter(stock_actual__lt=F('stock_minimo'))

    # Contar productos con stock bajo para mostrar alerta (sobre el listado ya filtrado)
    productos_stock_bajo = [p for p in productos if p.stock_bajo]

    # Obtener lista de proveedores activos para el formulario de crear producto
    proveedores = Proveedor.objects.filter(activo=True)

    return render(request, 'productos/inventario.html', {
        'productos': productos,
        'proveedores': proveedores,
        'busqueda': busqueda,
        'solo_stock_bajo': solo_stock_bajo,
        'productos_stock_bajo': productos_stock_bajo,
    })


@login_required(login_url='usuarios:login')
def crear_producto(request):
    """
    Crea un nuevo producto en el inventario.
    Recibe los datos del formulario por POST.
    """
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para realizar esta acción.')
        return redirect('core:home')

    if request.method == 'POST':
        # Obtener datos del formulario
        codigo = request.POST.get('codigo', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        precio = request.POST.get('precio', '').strip()
        stock_actual = request.POST.get('stock_actual', '').strip()
        stock_minimo = request.POST.get('stock_minimo', '').strip()
        proveedor_id = request.POST.get('proveedor', '').strip()

        # Diccionario para acumular errores
        errores = {}

        # Validar campos obligatorios
        if not codigo:
            errores['codigo'] = 'El código es obligatorio.'
        elif not CODIGO_PRODUCTO_REGEX.match(codigo):
            errores['codigo'] = 'El código debe tener el formato PROD-0000.'
        elif Producto.objects.filter(codigo__iexact=codigo).exists():
            errores['codigo'] = 'Ya existe un producto con ese código.'
        if not nombre:
            errores['nombre'] = 'El nombre es obligatorio.'
        if not precio:
            errores['precio'] = 'El precio es obligatorio.'

        # Validar que el precio sea un número válido
        precio_decimal = None
        if precio:
            try:
                precio_decimal = float(precio)
                if precio_decimal < 0:
                    errores['precio'] = 'El precio no puede ser negativo.'
            except ValueError:
                errores['precio'] = 'El precio debe ser un número válido.'

        # Validar que el stock sea un número entero válido
        stock_actual_int = 0
        if stock_actual:
            try:
                stock_actual_int = int(stock_actual)
                if stock_actual_int < 0:
                    errores['stock_actual'] = 'El stock no puede ser negativo.'
            except ValueError:
                errores['stock_actual'] = 'El stock debe ser un número entero.'

        # Validar stock mínimo
        stock_minimo_int = 5
        if stock_minimo:
            try:
                stock_minimo_int = int(stock_minimo)
                if stock_minimo_int < 0:
                    errores['stock_minimo'] = 'El stock mínimo no puede ser negativo.'
            except ValueError:
                errores['stock_minimo'] = 'El stock mínimo debe ser un número entero.'

        # Buscar el proveedor si se seleccionó uno
        proveedor = None
        if proveedor_id:
            try:
                proveedor = Proveedor.objects.get(id=proveedor_id, activo=True)
            except (Proveedor.DoesNotExist, ValueError):
                errores['proveedor'] = 'Proveedor no encontrado.'

        # Si hay errores, volver al inventario con los errores
        if errores:
            productos = Producto.objects.filter(activo=True).select_related('proveedor')
            proveedores = Proveedor.objects.filter(activo=True)
            productos_stock_bajo = [p for p in productos if p.stock_bajo]
            return render(request, 'productos/inventario.html', {
                'productos': productos,
                'proveedores': proveedores,
                'errores': errores,
                'productos_stock_bajo': productos_stock_bajo,
                # Mantener los datos que el usuario escribió
                'form_codigo': codigo,
                'form_nombre': nombre,
                'form_descripcion': descripcion,
                'form_precio': precio,
                'form_stock_actual': stock_actual,
                'form_stock_minimo': stock_minimo,
            })

        # Crear el producto en la base de datos
        Producto.objects.create(
            codigo=codigo,
            nombre=nombre,
            descripcion=descripcion,
            precio=precio_decimal,
            stock_actual=stock_actual_int,
            stock_minimo=stock_minimo_int,
            proveedor=proveedor,
        )

        messages.success(request, f'Producto "{nombre}" creado correctamente.')
        return redirect('productos:inventario')

    # Si no es POST, redirigir al inventario
    return redirect('productos:inventario')


@login_required(login_url='usuarios:login')
def editar_producto(request, producto_id):
    """
    Edita un producto existente del inventario.
    GET: muestra el formulario con los datos actuales.
    POST: guarda los cambios.
    """
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para realizar esta acción.')
        return redirect('core:home')

    # Obtener el producto o mostrar error 404
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == 'POST':
        # Obtener datos del formulario
        codigo = request.POST.get('codigo', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        precio = request.POST.get('precio', '').strip()
        stock_actual = request.POST.get('stock_actual', '').strip()
        stock_minimo = request.POST.get('stock_minimo', '').strip()
        proveedor_id = request.POST.get('proveedor', '').strip()

        # Diccionario para acumular errores
        errores = {}

        # Validar campos obligatorios
        if not codigo:
            errores['codigo'] = 'El código es obligatorio.'
        elif not CODIGO_PRODUCTO_REGEX.match(codigo):
            errores['codigo'] = 'El código debe tener el formato PROD-0000.'
        elif Producto.objects.filter(codigo__iexact=codigo).exclude(id=producto.id).exists():
            errores['codigo'] = 'Ya existe un producto con ese código.'
        if not nombre:
            errores['nombre'] = 'El nombre es obligatorio.'
        if not precio:
            errores['precio'] = 'El precio es obligatorio.'

        # Validar precio
        precio_decimal = None
        if precio:
            try:
                precio_decimal = float(precio)
                if precio_decimal < 0:
                    errores['precio'] = 'El precio no puede ser negativo.'
            except ValueError:
                errores['precio'] = 'El precio debe ser un número válido.'

        # Validar stock actual
        stock_actual_int = 0
        if stock_actual:
            try:
                stock_actual_int = int(stock_actual)
                if stock_actual_int < 0:
                    errores['stock_actual'] = 'El stock no puede ser negativo.'
            except ValueError:
                errores['stock_actual'] = 'El stock debe ser un número entero.'

        # Validar stock mínimo
        stock_minimo_int = 5
        if stock_minimo:
            try:
                stock_minimo_int = int(stock_minimo)
                if stock_minimo_int < 0:
                    errores['stock_minimo'] = 'El stock mínimo no puede ser negativo.'
            except ValueError:
                errores['stock_minimo'] = 'El stock mínimo debe ser un número entero.'

        # Buscar el proveedor si se seleccionó uno (se acepta el actual aunque esté desactivado)
        proveedor = None
        if proveedor_id:
            try:
                proveedor = Proveedor.objects.filter(
                    Q(activo=True) | Q(id=producto.proveedor_id)
                ).get(id=proveedor_id)
            except (Proveedor.DoesNotExist, ValueError):
                errores['proveedor'] = 'Proveedor no encontrado.'

        # Si hay errores, volver a mostrar el formulario
        if errores:
            proveedores = Proveedor.objects.filter(Q(activo=True) | Q(id=producto.proveedor_id))
            return render(request, 'productos/editar_producto.html', {
                'producto': producto,
                'proveedores': proveedores,
                'errores': errores,
            })

        # Actualizar los datos del producto
        producto.codigo = codigo
        producto.nombre = nombre
        producto.descripcion = descripcion
        producto.precio = precio_decimal
        producto.stock_actual = stock_actual_int
        producto.stock_minimo = stock_minimo_int
        producto.proveedor = proveedor
        # Guardar cambios en la base de datos
        producto.save()

        messages.success(request, f'Producto "{nombre}" actualizado correctamente.')
        return redirect('productos:inventario')

    # GET: mostrar formulario con datos actuales del producto
    proveedores = Proveedor.objects.filter(Q(activo=True) | Q(id=producto.proveedor_id))
    return render(request, 'productos/editar_producto.html', {
        'producto': producto,
        'proveedores': proveedores,
    })


@login_required(login_url='usuarios:login')
def desactivar_producto(request, producto_id):
    """
    Desactiva un producto (soft delete).
    No se elimina de la BD, solo se marca como inactivo.
    """
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para realizar esta acción.')
        return redirect('core:home')

    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == 'POST':
        # Cambiar estado a inactivo
        producto.activo = False
        producto.save()
        messages.success(request, f'Producto "{producto.nombre}" desactivado.')

    return redirect('productos:inventario')

@login_required(login_url='usuarios:login')
def proveedores(request):
    """Lista, crea, edita y activa/desactiva proveedores de productos."""
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    lista = Proveedor.objects.annotate(total_productos=Count('productos'))

    proveedor_editar = None
    editar_id = request.GET.get('editar')
    if editar_id:
        proveedor_editar = get_object_or_404(Proveedor, id=editar_id)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'guardar':
            errores = {}
            proveedor_id = request.POST.get('proveedor_id')
            if proveedor_id:
                proveedor_editar = get_object_or_404(Proveedor, id=proveedor_id)

            datos = {
                'nombre':   request.POST.get('nombre', '').strip(),
                'telefono': request.POST.get('telefono', '').strip(),
                'email':    request.POST.get('email', '').strip(),
            }

            if not datos['nombre']:
                errores['nombre'] = 'El nombre es obligatorio.'
            else:
                repetido = Proveedor.objects.filter(nombre__iexact=datos['nombre'])
                if proveedor_editar:
                    repetido = repetido.exclude(id=proveedor_editar.id)
                if repetido.exists():
                    errores['nombre'] = 'Ya existe un proveedor con ese nombre.'

            if datos['telefono'] and not re.match(r'^\d{4}-\d{4}$', datos['telefono']):
                errores['telefono'] = 'El teléfono debe tener formato 0000-0000.'

            if datos['email']:
                try:
                    validate_email(datos['email'])
                except ValidationError:
                    errores['email'] = 'Ingresá un correo válido.'

            if errores:
                return render(request, 'productos/proveedores.html', {
                    'proveedores': lista,
                    'errores': errores,
                    'datos': datos,
                    'proveedor_editar': proveedor_editar,
                    'mostrar_form': True,
                })

            if proveedor_editar:
                proveedor_editar.nombre = datos['nombre']
                proveedor_editar.telefono = datos['telefono']
                proveedor_editar.email = datos['email']
                proveedor_editar.save()
                messages.success(request, f'Proveedor "{proveedor_editar.nombre}" actualizado.')
            else:
                Proveedor.objects.create(
                    nombre=datos['nombre'],
                    telefono=datos['telefono'],
                    email=datos['email'],
                )
                messages.success(request, f'Proveedor "{datos["nombre"]}" creado.')

            return redirect('productos:proveedores')

        elif accion == 'desactivar':
            proveedor = get_object_or_404(Proveedor, id=request.POST.get('proveedor_id'))
            proveedor.activo = False
            proveedor.save(update_fields=['activo'])
            messages.success(request, f'Proveedor "{proveedor.nombre}" desactivado.')
            return redirect('productos:proveedores')

        elif accion == 'activar':
            proveedor = get_object_or_404(Proveedor, id=request.POST.get('proveedor_id'))
            proveedor.activo = True
            proveedor.save(update_fields=['activo'])
            messages.success(request, f'Proveedor "{proveedor.nombre}" activado.')
            return redirect('productos:proveedores')

    return render(request, 'productos/proveedores.html', {
        'proveedores': lista,
        'errores': {},
        'datos': {},
        'proveedor_editar': proveedor_editar,
        'mostrar_form': bool(request.GET.get('mostrar_form') or proveedor_editar),
    })
