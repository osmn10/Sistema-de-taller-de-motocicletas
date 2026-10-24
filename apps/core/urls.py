"""URLs de la app core: landing y paneles por rol."""

from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('panel-mecanico/', views.panel_mecanico, name='panel_mecanico'),
]
