"""URLs de la app productos."""

from django.urls import path

from . import views

app_name = 'productos'

urlpatterns = [
    path('', views.inventario, name='inventario'),
]
