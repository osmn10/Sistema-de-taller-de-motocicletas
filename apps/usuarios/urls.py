# Importar la función path para definir rutas URL
from django.urls import path

# Importar las vistas que creamos en views.py
from .views import LoginView, LogoutView

# app_name define el namespace (espacio de nombres) de esta app
# Permite usar {% url 'usuarios:login' %} en los templates
app_name = 'usuarios'

# urlpatterns es la lista de URLs que maneja esta app
urlpatterns = [
    # Ruta para el login
    # URL: /usuarios/login/
    # Vista: LoginView (maneja GET y POST)
    # name: identificador para usar en templates y redirects
    path('login/', LoginView.as_view(), name='login'),
    
    # Ruta para el logout (cerrar sesión)
    # URL: /usuarios/logout/
    # Vista: LogoutView
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # NOTA: Estas rutas las crearás después cuando hagas el registro
    # path('registro/', RegistroView.as_view(), name='registro'),
    # path('recuperar-password/', RecuperarPasswordView.as_view(), name='recuperar_password'),
]