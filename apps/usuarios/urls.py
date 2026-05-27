"""URLs de la app usuarios."""

from django.urls import path

from . import views
from .views import LoginView, LogoutView

# app_name hace que estas URLs vivan en el namespace "usuarios".
# Eso permite escribir {% url 'usuarios:login' %} en los templates
# sin que choque con un 'login' de otra app.
app_name = 'usuarios'

urlpatterns = [
    # --- Autenticación ---
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('registro/', views.registro_cliente, name='registro_cliente'),

    # Perfil del usuario logueado (placeholder, lo implementa SCRUM-43)
    path('mi-perfil/', views.mi_perfil, name='mi_perfil'),

    # --- CRUD de clientes (SCRUM-29, solo admin) ---
    # El <str:dui> captura el DUI desde la URL y lo pasa como argumento
    # a la vista. Como nuestro DUI es del estilo "00000000-0", uso str.
    path('clientes/', views.clientes_lista, name='clientes_lista'),
    path('clientes/<str:dui>/', views.cliente_detalle, name='cliente_detalle'),
    path('clientes/<str:dui>/editar/', views.cliente_editar, name='cliente_editar'),
    path('clientes/<str:dui>/toggle/', views.cliente_toggle, name='cliente_toggle'),

    # Gestión de mecánicos y admins (placeholder, otro PBI)
    path('usuarios/', views.usuarios_lista, name='usuarios_lista'),
]
