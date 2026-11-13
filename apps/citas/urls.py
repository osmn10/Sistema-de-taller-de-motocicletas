"""URLs de la app citas."""

from django.urls import path

from . import views

app_name = 'citas'

urlpatterns = [
    path('mis-citas/', views.mis_citas, name='mis_citas'),
    path('mis-citas/<int:cita_id>/', views.cita_detalle, name='cita_detalle'),
    path('mis-citas/<int:cita_id>/ticket/', views.descargar_ticket, name='descargar_ticket'),
    path('mis-citas/<int:cita_id>/comprobante/', views.descargar_comprobante, name='descargar_comprobante'),
    path('mis-citas/<int:cita_id>/cancelar/', views.cancelar_cita, name='cancelar_cita'),
    path('mis-citas/<int:cita_id>/reagendar/', views.reagendar_cita, name='reagendar_cita'),
    path('mis-citas/<int:cita_id>/calificar/', views.calificar_cita, name='calificar_cita'),
    path('disponibilidad/', views.disponibilidad, name='disponibilidad'),
    path('agendar/', views.agendar_cita, name='agendar_cita'),
    path('calendario/', views.calendario, name='calendario'),
    path('calendario/<int:cita_id>/', views.cita_admin_detalle, name='cita_admin_detalle'),
    path('mis-citas-mecanico/', views.mis_citas_mecanico, name='mis_citas_mecanico'),
    path('estados/', views.estados_cita, name='estados_cita'),
    path('reporte/', views.reporte_servicios, name='reporte_servicios'),
    path('calificaciones/', views.calificaciones, name='calificaciones'),
    # HU031: correos de cita fallidos y su reintento
    path('envios-correo/', views.envios_correo, name='envios_correo'),
    path('envios-correo/<int:envio_id>/reintentar/', views.reintentar_envio_correo, name='reintentar_envio_correo'),
]