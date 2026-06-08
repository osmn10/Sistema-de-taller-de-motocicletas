"""URLs de la app productos."""

from django.urls import path
from . import views

# Namespace para usar en templates: productos:inventario, productos:crear, etc.
app_name = 'productos'

urlpatterns = [
    # Lista de productos: /productos/inventario/
    path('inventario/', views.inventario, name='inventario'),
    # Crear producto: /productos/crear/ (solo POST)
    path('crear/', views.crear_producto, name='crear_producto'),
    # Editar producto: /productos/5/editar/
    path('<int:producto_id>/editar/', views.editar_producto, name='editar_producto'),
    # Desactivar producto: /productos/5/desactivar/ (solo POST)
    path('<int:producto_id>/desactivar/', views.desactivar_producto, name='desactivar_producto'),
]