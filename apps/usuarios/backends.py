"""
Backend de autenticación custom para el sistema.

Permite iniciar sesión con DUI o Email + contraseña.
Django por defecto solo acepta username + password, pero aquí
extendemos esa funcionalidad para aceptar dos tipos de identificadores.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.db.models import Q

# Obtener el modelo de Usuario configurado en el proyecto
User = get_user_model()


class DUIorEmailBackend(BaseBackend):
    """
    Backend de autenticación que acepta DUI o Email como identificador.
    
    Cuando el usuario envía el formulario de login, este backend:
    1. Busca en la base de datos un usuario que tenga ese DUI O ese email
    2. Verifica que la contraseña sea correcta
    3. Verifica que el usuario esté activo (activo=True)
    4. Si todo es correcto, devuelve el objeto User
    5. Si algo falla, devuelve None
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Método principal de autenticación.
        
        Args:
            request: La petición HTTP actual
            username: El identificador que el usuario escribió (puede ser DUI o email)
            password: La contraseña que el usuario escribió
            **kwargs: Otros parámetros opcionales
        
        Returns:
            User: Si las credenciales son válidas y el usuario está activo
            None: Si las credenciales son inválidas o el usuario está inactivo
        """
        
        # Si no se proporcionó username o password, retornar None
        if username is None or password is None:
            return None
        
        try:
            # Buscar el usuario en la base de datos
            # Q() permite hacer búsquedas con OR (O lógico)
            # Busca un usuario donde dui=username O email=username
            user = User.objects.get(
                Q(dui=username) | Q(email=username)
            )
            
            # Verificar que la contraseña sea correcta
            # check_password() hashea la contraseña ingresada y la compara con la almacenada
            if user.check_password(password):
                # Verificar que el usuario esté activo
                if user.activo:
                    # ✅ TODO CORRECTO: devolver el usuario
                    return user
                else:
                    # ❌ Usuario desactivado
                    return None
            else:
                # ❌ Contraseña incorrecta
                return None
        
        except User.DoesNotExist:
            # ❌ No existe un usuario con ese DUI o email
            return None
        
        except User.MultipleObjectsReturned:
            # ❌ Error de integridad: hay múltiples usuarios (no debería pasar)
            return None
    
    def get_user(self, user_id):
        """
        Obtener un usuario por su ID (DUI en este caso).
        
        Django llama este método para recuperar el usuario de la sesión.
        
        Args:
            user_id: El DUI del usuario (primary key)
        
        Returns:
            User: Si existe un usuario con ese DUI
            None: Si no existe
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None