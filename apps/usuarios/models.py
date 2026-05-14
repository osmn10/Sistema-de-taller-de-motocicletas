from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    """Modelo de usuario base del sistema.

    Por ahora hereda de AbstractUser sin campos adicionales. Los campos
    propios del dominio (rol, teléfono, etc.) se agregarán en iteraciones
    posteriores.
    """

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
