"""V2SCRUM-30: genera el ticket PDF del servicio.

Se apoya en ``calcular_detalle_cita`` (V2SCRUM-27) como única fuente de
verdad para los importes: no vuelve a sumar precios del catálogo ni
persiste el PDF en disco/BD. Se genera "al vuelo" cada vez que se pide
(al finalizar, para adjuntar al correo, o al descargarlo desde el
historial del cliente), a partir de las líneas ya guardadas de la cita.
"""

from io import BytesIO

from django.conf import settings
from django.utils.html import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _money(valor):
    return f'${valor:.2f}' if valor is not None else 'N/D'


def generar_ticket_pdf(cita, detalle) -> bytes:
    """Arma el PDF del ticket. ``detalle`` es el resultado de
    ``calcular_detalle_cita(cita)``, para no recalcularlo si el llamador
    ya lo tiene (p. ej. el correo de cierre)."""

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title=f'Ticket de servicio - Cita #{cita.id}',
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(escape(settings.TALLER_NOMBRE), styles['Title']))
    story.append(Paragraph(f'Ticket de servicio — Cita #{cita.id}', styles['Heading2']))
    story.append(Spacer(1, 10))

    datos_cliente = (
        f'<b>Cliente:</b> {escape(cita.cliente.nombre)} {escape(cita.cliente.apellido)}<br/>'
        f'<b>Motocicleta:</b> {escape(str(cita.motocicleta))}<br/>'
        f'<b>Fecha:</b> {cita.fecha.strftime("%d/%m/%Y")} — '
        f'<b>Hora:</b> {cita.hora.strftime("%H:%M")}'
    )
    story.append(Paragraph(datos_cliente, styles['Normal']))
    story.append(Spacer(1, 16))

    # --- Servicios ---
    story.append(Paragraph('Servicios prestados', styles['Heading3']))
    filas_servicios = [['Servicio', 'Precio']]
    for linea in detalle['servicios']:
        filas_servicios.append([escape(linea['nombre']), _money(linea['precio'])])
    filas_servicios.append(['Subtotal servicios', _money(detalle['subtotal_servicios'])])

    tabla_servicios = Table(filas_servicios, colWidths=[110 * mm, 40 * mm])
    tabla_servicios.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    story.append(tabla_servicios)
    story.append(Spacer(1, 14))

    # --- Repuestos (solo si hay) ---
    if detalle['repuestos']:
        story.append(Paragraph('Repuestos e insumos utilizados', styles['Heading3']))
        filas_repuestos = [['Producto', 'Cant.', 'Precio unit.', 'Importe']]
        for linea in detalle['repuestos']:
            nombre = escape(linea['nombre'])
            if linea['estimado']:
                nombre += ' (referencial)'
            filas_repuestos.append([
                nombre,
                str(linea['cantidad']),
                _money(linea['precio_unitario']),
                _money(linea['importe']),
            ])
        filas_repuestos.append(['', '', 'Subtotal repuestos', _money(detalle['subtotal_repuestos'])])

        tabla_repuestos = Table(filas_repuestos, colWidths=[70 * mm, 20 * mm, 30 * mm, 30 * mm])
        tabla_repuestos.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ]))
        story.append(tabla_repuestos)
        story.append(Spacer(1, 14))

    # --- Total ---
    if detalle['errores']:
        story.append(Paragraph(
            'No fue posible calcular un total válido para esta cita. '
            'Consultá con el taller para más detalle.',
            styles['Normal'],
        ))
    else:
        etiqueta = 'Total referencial' if detalle['es_referencial'] else 'Total'
        story.append(Paragraph(
            f'<b>{etiqueta}: {_money(detalle["total_referencia"])}</b>',
            styles['Heading2'],
        ))
        if detalle['es_referencial']:
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                'Incluye repuestos anteriores sin precio histórico guardado; '
                'se usó su precio actual solo como referencia.',
                styles['Normal'],
            ))

    if cita.observaciones_cierre:
        story.append(Spacer(1, 14))
        story.append(Paragraph('Observaciones', styles['Heading3']))
        story.append(Paragraph(escape(cita.observaciones_cierre), styles['Normal']))

    story.append(Spacer(1, 20))
    story.append(Paragraph('Gracias por confiar en nosotros.', styles['Normal']))

    doc.build(story)
    return buffer.getvalue()