"""V2SCRUM-36: genera el comprobante PDF de una cita agendada.

Es la constancia de la reserva, no del servicio realizado (eso es el ticket
de V2SCRUM-30). Se genera "al vuelo" cada vez que el cliente lo pide, a
partir de los datos guardados de la cita; no se persiste en disco ni en BD.
"""

from io import BytesIO

from django.conf import settings
from django.utils import timezone
from django.utils.html import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def numero_comprobante(cita):
    """Identificador único del comprobante, derivado del id de la cita (p. ej. CITA-000042)."""
    return f'CITA-{cita.id:06d}'


def generar_comprobante_pdf(cita) -> bytes:
    """Arma el PDF del comprobante con fecha, hora, servicios y motocicleta de la cita."""

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title=f'Comprobante de cita - {numero_comprobante(cita)}',
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(escape(settings.TALLER_NOMBRE), styles['Title']))
    story.append(Paragraph('Comprobante de cita agendada', styles['Heading2']))
    story.append(Paragraph(f'<b>N.º de comprobante:</b> {numero_comprobante(cita)}', styles['Normal']))
    story.append(Paragraph(
        f'<b>Emitido:</b> {timezone.localtime().strftime("%d/%m/%Y %H:%M")}',
        styles['Normal'],
    ))
    story.append(Spacer(1, 14))

    # --- Datos de la reserva ---
    datos_reserva = [
        ['Cliente', f'{cita.cliente.nombre} {cita.cliente.apellido}'],
        ['Motocicleta', str(cita.motocicleta)],
        ['Fecha', cita.fecha.strftime('%d/%m/%Y')],
        ['Hora', cita.hora.strftime('%H:%M')],
        ['Estado', cita.estado.nombre],
    ]
    tabla_reserva = Table(
        [[Paragraph(f'<b>{etiqueta}</b>', styles['Normal']), Paragraph(escape(valor), styles['Normal'])]
         for etiqueta, valor in datos_reserva],
        colWidths=[40 * mm, 110 * mm],
    )
    tabla_reserva.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(tabla_reserva)
    story.append(Spacer(1, 14))

    # --- Servicios solicitados (precio guardado al agendar) ---
    story.append(Paragraph('Servicios solicitados', styles['Heading3']))
    filas_servicios = [['Servicio', 'Precio de referencia']]
    for linea in cita.serviciocita_set.select_related('servicio').all():
        filas_servicios.append([escape(linea.servicio.nombre), f'${linea.precio_final:.2f}'.replace('.', ',')])
    if len(filas_servicios) == 1:
        filas_servicios.append(['Sin servicios registrados', ''])

    tabla_servicios = Table(filas_servicios, colWidths=[110 * mm, 40 * mm])
    tabla_servicios.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    story.append(tabla_servicios)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        'El total final se confirma al cerrar el servicio e incluye los repuestos utilizados.',
        styles['Italic'],
    ))

    if cita.observaciones:
        story.append(Spacer(1, 12))
        story.append(Paragraph('Observaciones', styles['Heading3']))
        story.append(Paragraph(escape(cita.observaciones), styles['Normal']))

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        'Presentá este comprobante el día de tu cita. Si necesitás cancelar o reagendar, '
        'hacelo desde la sección Mis citas del sistema.',
        styles['Normal'],
    ))

    contacto = [settings.TALLER_TELEFONO, settings.TALLER_DIRECCION, settings.TALLER_EMAIL_CONTACTO]
    contacto = ' · '.join(escape(dato) for dato in contacto if dato)
    if contacto:
        story.append(Spacer(1, 8))
        story.append(Paragraph(contacto, styles['Normal']))

    doc.build(story)
    return buffer.getvalue()
