# V2SCRUM-27 — Detalle y total del servicio

## Alcance

El detalle administrativo muestra los servicios de la cita, los repuestos e
insumos utilizados, cantidades, precios unitarios, importes y ambos subtotales.
Total = suma de ServicioCita.precio_final + suma de cantidad × precio_unitario.
Se mantienen los precios de servicios ya registrados; no se redefine el catálogo
ni se crean paquetes, descuentos, impuestos, un flujo de pago o nuevos estados.

El cliente también ve este desglose al abrir el detalle de una cita Completada.
Se conserva el filtro por propietario: no puede consultar citas de otro cliente.
Usa calcular_detalle_cita, igual que el administrador, y conserva las advertencias
para precios históricos faltantes. No incorpora edición, PDF ni nuevos correos.

El formulario de Lorezenny conserva su selección manual de productos. Una vista
previa actualiza los importes al agregar, quitar o modificar filas. JavaScript usa
centavos enteros; el servidor usa Decimal y no acepta un total del navegador.
La vista previa usa los precios que cargó la página. El cierre valida de nuevo
los precios de los productos y el stock vigentes en el servidor.

Antes de enviar, el navegador bloquea las filas incompletas, cantidades no enteras
o menores a uno y productos repetidos. Muestra el error junto al campo y un aviso
persistente al intentar finalizar, sin recargar ni perder selecciones. Una fila
totalmente vacía sigue siendo opcional. El servidor mantiene su validación como
respaldo si JavaScript está desactivado o la petición se envía directamente.

## Precio histórico y migración

La migración 0004 agrega RepuestoUsado.precio_unitario. Las nuevas finalizaciones
lo guardan junto con el consumo dentro de la transacción existente. Los servicios
ya conservaban precio_final al agendar. Cambiar el catálogo después no altera
estos importes guardados. No se duplica una columna de total: se deriva de las
líneas históricas con una función compartida.

Los consumos anteriores quedan con precio_unitario NULL: no se conoce su precio
histórico. La pantalla los identifica como REFERENCIALES y usa el catálogo actual
solo para orientar. No se modifica ni inventa un cobro anterior. Esa referencia
puede variar si cambia el catálogo; no debe usarse en un comprobante definitivo.

Aplicar en cada entorno, después de respaldar su base:

```bash
python manage.py migrate
```

## Integración para ticket, correo, reportes y dashboard

```python
from apps.citas.totales import calcular_detalle_cita

detalle = calcular_detalle_cita(cita)
if detalle['total'] is None:
    # Mostrar/resolver precios inválidos o históricos faltantes.
    # No emitir un importe definitivo a partir de total_referencia.
    ...
else:
    total = detalle['total']  # Decimal; cero también es válido.
```

La función devuelve servicios, repuestos, subtotal_servicios, subtotal_repuestos,
total, total_referencia, es_referencial y errores. No cambia stock ni estado.
Los futuros consumidores deben usar esta función, no volver a sumar con precios
del catálogo. Para documentos de cierre, verificar además que la cita está
Completada. La integración efectiva de PDF/correo/reportes/dashboard corresponde
a sus respectivos PBIs y no se incluye en este cambio.

## Verificación

```bash
python manage.py test apps.core apps.citas --settings=config.settings.testing
```

Prueba manual: abrir una cita En proceso, seleccionar productos y cantidades,
revisar los subtotales y el total, quitar/cambiar filas y finalizar. En el detalle
Completada deben coincidir los importes con las líneas guardadas y el stock debe
descontarse una sola vez. No finalizar citas reales únicamente para probar.

El cierre existente no se rediseña en este PBI. La prueba de segundo cierre es
secuencial; no acredita protección frente a dos solicitudes concurrentes.

### Entorno local de pruebas

Las pruebas GET del detalle usan RequestFactory y renderizan la vista real sin
el recolector de contextos de Client. Django 5.1 con Python 3.14 tiene una
incompatibilidad conocida al copiar Context; no se alteraron dependencias ni se
parcheó Django. El detalle permanece en su plantilla administrativa, y el cálculo
y la interacción JavaScript están separados en sus propios archivos.
Referencia: https://code.djangoproject.com/ticket/35844
