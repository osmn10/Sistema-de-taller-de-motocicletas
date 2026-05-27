"""URLs de la app vehiculos."""

from django.urls import path

from . import views

app_name = 'vehiculos'

urlpatterns = [
    path('', views.mis_motos, name='mis_motos'),
    path('nueva/', views.motos_form, name='motos_form'),
]
