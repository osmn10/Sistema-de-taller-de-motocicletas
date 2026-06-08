"""URLs de la app configuracion."""

from django.urls import path

from . import views

app_name = 'configuracion'

urlpatterns = [
    path('horario/', views.horario, name='horario'),
]
