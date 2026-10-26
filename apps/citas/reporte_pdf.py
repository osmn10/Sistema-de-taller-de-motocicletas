"""V2SCRUM-39: genera el PDF del reporte de servicios por período.

Mismo patrón que ``ticket_pdf.py`` (V2SCRUM-30): se arma "al vuelo" a
partir del dict que devuelve ``calcular_reporte_servicios``, sin persistir
nada en disco/BD.
"""

from io import BytesIO

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


def _tabla_ranking(titulo, filas, etiqueta_nombre, styles):
    """Arma el título + tabla de un ranking (servicios o mecánicos)."""
    bloque = [Paragraph(titulo, styles['Heading3'])]
    cuerpo = [[etiqueta_nombre, 'Cantidad']] + filas
    if len(cuerpo) == 1:
        cuerpo.append(['Sin datos en el período.', ''])
    tabla = Table(cuerpo, colWidths=[110 * mm, 40 * mm])
    tabla.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    bloque.append(tabla)
    bloque.append(Spacer(1, 16))
    return bloque


def generar_reporte_pdf(desde, hasta, datos) -> bytes:
    """Arma el PDF del reporte. ``datos`` es el resultado de
    ``calcular_reporte_servicios``."""

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title='Reporte de servicios',
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph('Reporte de servicios', styles['Title']))
    story.append(Paragraph(
        f'Período: {desde.strftime("%d/%m/%Y")} — {hasta.strftime("%d/%m/%Y")}',
        styles['Heading3'],
    ))
    story.append(Spacer(1, 14))

    resumen = [
        ['Citas del período', str(datos['total_citas'])],
        ['Servicios completados', str(datos['servicios_completados'])],
        ['Ingresos totales', _money(datos['ingresos_totales'])],
    ]
    tabla_resumen = Table(resumen, colWidths=[100 * mm, 50 * mm])
    tabla_resumen.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    story.append(tabla_resumen)
    story.append(Spacer(1, 18))

    filas_servicios = [
        [fila['servicio__nombre'], str(fila['cantidad'])]
        for fila in datos['servicios_top']
    ]
    story += _tabla_ranking('Servicios más solicitados', filas_servicios, 'Servicio', styles)

    filas_mecanicos = [
        [f"{fila['mecanico__nombre']} {fila['mecanico__apellido']}", str(fila['cantidad'])]
        for fila in datos['mecanicos_top']
    ]
    story += _tabla_ranking('Mecánico con más servicios', filas_mecanicos, 'Mecánico', styles)

    doc.build(story)
    return buffer.getvalue()
