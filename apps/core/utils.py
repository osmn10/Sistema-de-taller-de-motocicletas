"""Utilidades generales del proyecto."""

from datetime import date


def rango_fechas(request):
    """Lee ?desde= y ?hasta= (YYYY-MM-DD) de la querystring.

    Por defecto toma desde el día 1 del mes actual hasta hoy. Si las fechas
    vienen invertidas se intercambian; si vienen mal formadas se ignoran.
    Compartida por el dashboard (V2SCRUM-40) y el reporte de servicios
    (V2SCRUM-39) para que ambos filtren igual.
    """
    hoy = date.today()

    try:
        desde_str = request.GET.get('desde', '')
        desde = date.fromisoformat(desde_str) if desde_str else hoy.replace(day=1)
    except ValueError:
        desde = hoy.replace(day=1)

    try:
        hasta_str = request.GET.get('hasta', '')
        hasta = date.fromisoformat(hasta_str) if hasta_str else hoy
    except ValueError:
        hasta = hoy

    if hasta < desde:
        desde, hasta = hasta, desde

    return desde, hasta
