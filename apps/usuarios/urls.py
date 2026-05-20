"""URLs de la app usuarios."""

from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('registro/', views.registro_cliente, name='registro_cliente'),
]
