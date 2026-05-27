"""URLs de la app vehiculos."""

from django.urls import path

from . import views

app_name = 'vehiculos'

urlpatterns = [
    path('', views.mis_motos, name='mis_motos'),
    path('nueva/', views.moto_crear, name='moto_crear'),
    path('<str:placa>/editar/', views.moto_editar, name='moto_editar'),
    path('<str:placa>/toggle/', views.moto_toggle, name='moto_toggle'),
]
