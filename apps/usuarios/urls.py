"""URLs de la app usuarios."""

from django.urls import path

from . import views
from .views import LoginView, LogoutView

app_name = 'usuarios'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('registro/', views.registro_cliente, name='registro_cliente'),
    path('mi-perfil/', views.mi_perfil, name='mi_perfil'),
    path('clientes/', views.clientes_lista, name='clientes_lista'),
    path('clientes/<str:dui>/', views.cliente_detalle, name='cliente_detalle'),
    path('clientes/<str:dui>/editar/', views.cliente_editar, name='cliente_editar'),
    path('clientes/<str:dui>/toggle/', views.cliente_toggle, name='cliente_toggle'),
    path('usuarios/', views.usuarios_lista, name='usuarios_lista'),
]
