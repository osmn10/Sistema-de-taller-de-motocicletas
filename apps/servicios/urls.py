"""URLs de la app servicios."""

from django.urls import path

from . import views

app_name = 'servicios'

urlpatterns = [
    path('catalogo/', views.catalogo_servicios, name='catalogo_servicios'),
]
