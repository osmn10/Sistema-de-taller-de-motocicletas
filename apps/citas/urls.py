"""URLs de la app citas."""

from django.urls import path

from . import views

app_name = 'citas'

urlpatterns = [
    path('mis-citas/', views.mis_citas, name='mis_citas'),
    path('mis-citas/<int:cita_id>/', views.cita_detalle, name='cita_detalle'),
    path('mis-citas/<int:cita_id>/ticket/', views.descargar_ticket, name='descargar_ticket'),
    path('mis-citas/<int:cita_id>/cancelar/', views.cancelar_cita, name='cancelar_cita'),
    path('mis-citas/<int:cita_id>/reagendar/', views.reagendar_cita, name='reagendar_cita'),
    path('disponibilidad/', views.disponibilidad, name='disponibilidad'),
    path('agendar/', views.agendar_cita, name='agendar_cita'),
    path('calendario/', views.calendario, name='calendario'),
    path('calendario/<int:cita_id>/', views.cita_admin_detalle, name='cita_admin_detalle'),
    path('mis-citas-mecanico/', views.mis_citas_mecanico, name='mis_citas_mecanico'),
]