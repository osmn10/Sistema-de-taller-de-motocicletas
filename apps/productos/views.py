"""Vistas de la app productos — CRUD de inventario de repuestos."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Producto, Proveedor


@login_required(login_url='usuarios:login')
def inventario(request):
    """
    Lista todos los productos del inventario.
    Permite buscar por nombre o proveedor.
    Muestra alerta si hay productos con stock bajo.
    """
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    # Obtener el término de búsqueda del parámetro GET (si existe)
    busqueda = request.GET.get('q', '').strip()

    # Filtrar solo productos activos
    productos = Producto.objects.filter(activo=True).select_related('proveedor')

    # Si hay búsqueda, filtrar por nombre o proveedor
    if busqueda:
        productos = productos.filter(
            # __icontains busca texto sin importar mayúsculas/minúsculas
            nombre__icontains=busqueda
        ) | productos.filter(
            proveedor__nombre__icontains=busqueda
        )

    # Contar productos con stock bajo para mostrar alerta
    productos_stock_bajo = [p for p in productos if p.stock_bajo]

    # Obtener lista de proveedores activos para el formulario de crear producto
    proveedores = Proveedor.objects.filter(activo=True)

    return render(request, 'productos/inventario.html', {
        'productos': productos,
        'proveedores': proveedores,
        'busqueda': busqueda,
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
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        precio = request.POST.get('precio', '').strip()
        stock_actual = request.POST.get('stock_actual', '').strip()
        stock_minimo = request.POST.get('stock_minimo', '').strip()
        proveedor_nit = request.POST.get('proveedor', '').strip()

        # Diccionario para acumular errores
        errores = {}

        # Validar campos obligatorios
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
        if proveedor_nit:
            try:
                proveedor = Proveedor.objects.get(nit=proveedor_nit)
            except Proveedor.DoesNotExist:
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
                'form_nombre': nombre,
                'form_descripcion': descripcion,
                'form_precio': precio,
                'form_stock_actual': stock_actual,
                'form_stock_minimo': stock_minimo,
            })

        # Crear el producto en la base de datos
        Producto.objects.create(
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
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        precio = request.POST.get('precio', '').strip()
        stock_actual = request.POST.get('stock_actual', '').strip()
        stock_minimo = request.POST.get('stock_minimo', '').strip()
        proveedor_nit = request.POST.get('proveedor', '').strip()

        # Diccionario para acumular errores
        errores = {}

        # Validar campos obligatorios
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

        # Buscar el proveedor si se seleccionó uno
        proveedor = None
        if proveedor_nit:
            try:
                proveedor = Proveedor.objects.get(nit=proveedor_nit)
            except Proveedor.DoesNotExist:
                errores['proveedor'] = 'Proveedor no encontrado.'

        # Si hay errores, volver a mostrar el formulario
        if errores:
            proveedores = Proveedor.objects.filter(activo=True)
            return render(request, 'productos/editar_producto.html', {
                'producto': producto,
                'proveedores': proveedores,
                'errores': errores,
            })

        # Actualizar los datos del producto
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
    proveedores = Proveedor.objects.filter(activo=True)
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