# Importaciones necesarias de Django
from django.shortcuts import render, redirect  # render = mostrar templates, redirect = redirigir a otra URL
from django.contrib.auth import authenticate, login, logout  # Funciones de autenticación de Django
from django.contrib import messages  # Para mostrar mensajes flash (éxito, error, info)
from django.views import View  # Clase base para crear vistas basadas en clases


class LoginView(View):
    """
    Vista para manejar el inicio de sesión del sistema.
    
    Maneja dos métodos HTTP:
    - GET: Mostrar el formulario de login
    - POST: Procesar el formulario y autenticar al usuario
    """
    
    def get(self, request):
        """
        Método GET: Se ejecuta cuando el usuario accede a /login/
        
        Si el usuario ya tiene sesión activa, lo redirige según su rol.
        Si no, muestra el formulario de login.
        """
        # Verificar si el usuario ya está autenticado
        if request.user.is_authenticated:
            return self.redirect_by_role(request.user)
        
        # Renderizar el template login.html
        return render(request, 'usuarios/login.html')
    
    def post(self, request):
        """
        Método POST: Se ejecuta cuando el usuario envía el formulario de login
        
        1. Recibe los datos del formulario (DUI/email y contraseña)
        2. Valida que no estén vacíos
        3. Intenta autenticar al usuario
        4. Si es válido, inicia sesión y redirige según rol
        5. Si no, muestra mensaje de error
        """
        # Obtener los datos del formulario
        # request.POST es un diccionario con los datos enviados
        # .get('identifier', '') = obtiene el valor del campo 'identifier', si no existe devuelve ''
        # .strip() = elimina espacios en blanco al inicio y final
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')
        
        # VALIDACIÓN 1: Verificar que los campos no estén vacíos
        if not identifier or not password:
            # Si alguno está vacío, volver a mostrar el formulario con mensaje de error
            return render(request, 'usuarios/login.html', {
                'error': 'Por favor, complete todos los campos.'
            })
        
        # AUTENTICACIÓN: Verificar si las credenciales son correctas
        # authenticate() busca en la base de datos un usuario con esas credenciales
        # Si existe, devuelve el objeto User
        # Si no existe, devuelve None
        user = authenticate(request, username=identifier, password=password)
        
        # Verificar el resultado de la autenticación
        if user is not None:
            # ✅ CREDENCIALES CORRECTAS
            
            # login() crea la sesión del usuario (lo marca como autenticado)
            login(request, user)
            
            # messages.success() guarda un mensaje para mostrar en la próxima página
            messages.success(request, f'¡Bienvenido {user.nombre_completo}!')
            
            # Redirigir según el rol del usuario
            return self.redirect_by_role(user)
        else:
            # ❌ CREDENCIALES INCORRECTAS
            
            # Volver a mostrar el formulario con mensaje de error
            return render(request, 'usuarios/login.html', {
                'error': 'DUI/Email o contraseña incorrectos.'
            })
    
    def redirect_by_role(self, user):
        """
        Redirige al usuario a la página correspondiente según su rol.
        
        Roles en el sistema:
        1. Admin (is_staff=True) → /admin-panel/
        2. Mecánico (tiene relación con modelo Mecánico) → /panel-mecanico/
        3. Cliente (por defecto) → /mis-citas/
        """
        # Verificar si es administrador
        # is_staff = campo de Django que indica si es personal del sistema
        if user.is_staff:
            return redirect('admin-panel')
        
        # Verificar si es mecánico
        # hasattr(user, 'mecanico') = verifica si el usuario tiene relación con Mecánico
        if hasattr(user, 'mecanico'):
            return redirect('panel-mecanico')
        
        # Por defecto, es cliente
        return redirect('mis-citas')


class LogoutView(View):
    """
    Vista para cerrar la sesión del usuario.
    
    Simplemente destruye la sesión y redirige al login.
    """
    
    def get(self, request):
        """
        Método GET: Se ejecuta cuando el usuario hace click en "Cerrar sesión"
        """
        # logout() destruye la sesión del usuario
        logout(request)
        
        # Mostrar mensaje informativo
        messages.info(request, 'Has cerrado sesión correctamente.')
        
        # Redirigir al login
        return redirect('usuarios:login')