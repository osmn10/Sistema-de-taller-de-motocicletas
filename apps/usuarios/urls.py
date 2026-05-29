"""URLs de la app usuarios."""

from django.urls import path

from . import views
from .views import LoginView, LogoutView

app_name = 'usuarios'

urlpatterns = [
    path('registro/', views.registro_cliente, name='registro_cliente'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
