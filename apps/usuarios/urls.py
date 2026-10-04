"""URLs de la app usuarios."""

from django.urls import path

from . import views
from .views import LoginView, LogoutView

app_name = 'usuarios'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('registro/', views.registro_cliente, name='registro_cliente'),

    # V2SCRUM-34 · Recuperación de contraseña por correo
    path('password/recuperar/', views.password_reset_solicitar, name='password_reset_solicitar'),
    path('password/nueva/<uidb64>/<token>/', views.password_reset_confirmar, name='password_reset_confirmar'),

    path('mi-perfil/', views.mi_perfil, name='mi_perfil'),
    path('clientes/', views.clientes_lista, name='clientes_lista'),
    path('clientes/<str:dui>/', views.cliente_detalle, name='cliente_detalle'),
    path('clientes/<str:dui>/editar/', views.cliente_editar, name='cliente_editar'),
    path('clientes/<str:dui>/toggle/', views.cliente_toggle, name='cliente_toggle'),

    path('usuarios/', views.usuarios_lista, name='usuarios_lista'),
    path('usuarios/crear/', views.usuario_crear, name='usuario_crear'),
    path('usuarios/<str:dui>/editar/', views.usuario_editar, name='usuario_editar'),
    path('usuarios/<str:dui>/toggle/', views.usuario_toggle, name='usuario_toggle'),
    path('usuarios/<str:dui>/reset-password/', views.usuario_reset_password, name='usuario_reset_password'),
]
