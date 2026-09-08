"""V2SCRUM-27: fuente compartida del detalle económico de una cita.

Los consumidores deben usar ``total``; si es None, no existe un monto
histórico válido. ``total_referencia`` es solo una estimación para pantalla.
No modifica precios, inventario ni estados.
"""

from decimal import Decimal, InvalidOperation


CERO = Decimal('0.00')


def precio_valido(valor):
    try:
        precio = Decimal(str(valor))
        return precio.is_finite() and precio >= CERO
    except (InvalidOperation, ValueError, TypeError):
        return False


def calcular_detalle_cita(cita):
    servicios, repuestos, errores = [], [], []
    subtotal_servicios = CERO
    subtotal_repuestos = CERO
    es_referencial = False

    for linea in cita.serviciocita_set.select_related('servicio').all():
        precio = linea.precio_final
        if not precio_valido(precio):
            errores.append(f'El servicio "{linea.servicio.nombre}" no tiene un precio válido.')
        else:
            subtotal_servicios += precio
        servicios.append({'nombre': linea.servicio.nombre, 'precio': precio})

    for linea in cita.repuestos_usados.select_related('producto').all():
        estimado = linea.precio_unitario is None
        precio = linea.producto.precio if estimado else linea.precio_unitario
        es_referencial = es_referencial or estimado
        importe = None
        if not precio_valido(precio):
            errores.append(f'El repuesto "{linea.producto.nombre}" no tiene un precio válido.')
        else:
            importe = precio * linea.cantidad
            subtotal_repuestos += importe
        repuestos.append({
            'nombre': linea.producto.nombre, 'cantidad': linea.cantidad,
            'precio_unitario': precio, 'importe': importe, 'estimado': estimado,
        })

    referencia = None if errores else subtotal_servicios + subtotal_repuestos
    return {
        'servicios': servicios, 'repuestos': repuestos,
        'subtotal_servicios': subtotal_servicios,
        'subtotal_repuestos': subtotal_repuestos,
        'total': None if es_referencial else referencia,
        'total_referencia': referencia,
        'es_referencial': es_referencial, 'errores': errores,
    }
