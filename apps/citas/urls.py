"""URLs de la app citas."""

from django.urls import path

from . import views

app_name = 'citas'

urlpatterns = [
    path('mis-citas/', views.mis_citas, name='mis_citas'),
    path('mis-citas-mecanico/', views.mis_citas_mecanico, name='mis_citas_mecanico'),
    path('calendario/', views.calendario, name='calendario'),
    path('agendar/', views.agendar_cita, name='agendar_cita'),
    path('<int:cita_id>/', views.cita_detalle, name='cita_detalle'),
]
