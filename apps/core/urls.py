"""URLs de la app core: landing y paneles por rol."""

from django.urls import path

from . import views

# Namespace 'core' → en templates: {% url 'core:home' %}, {% url 'core:admin_panel' %}, etc.
app_name = 'core'

urlpatterns = [
    # Home pública (la ven los no autenticados o cualquier rol)
    path('', views.home, name='home'),
    # Panel principal después del login según el rol
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('panel-mecanico/', views.panel_mecanico, name='panel_mecanico'),
]
