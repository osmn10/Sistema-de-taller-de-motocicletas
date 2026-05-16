from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models

from .managers import UsuarioManager


dui_validator = RegexValidator(
    regex=r'^\d{8}-\d$',
    message='Formato de DUI inválido. Debe ser 00000000-0.',
)

telefono_validator = RegexValidator(
    regex=r'^\d{4}-\d{4}$',
    message='Formato de teléfono inválido. Debe ser 0000-0000.',
)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Modelo base de usuario del sistema.

    Usa el DUI como llave primaria. Los roles se determinan por herencia:
    Cliente y Mecánico son subclases; Admin es un Usuario con `is_staff=True`
    que no tiene subclase asociada.
    """

    dui = models.CharField(
        primary_key=True,
        max_length=10,
        validators=[dui_validator],
        verbose_name='DUI',
        help_text='Formato: 00000000-0',
    )
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(
        max_length=9,
        validators=[telefono_validator],
        help_text='Formato: 0000-0000',
    )
    email = models.EmailField(unique=True)
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Marcar como inactivo en lugar de eliminar.',
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    is_staff = models.BooleanField(
        default=False,
        verbose_name='Acceso al panel administrativo',
    )

    USERNAME_FIELD = 'dui'
    REQUIRED_FIELDS = ['nombre', 'apellido', 'email']

    objects = UsuarioManager()

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f'{self.nombre} {self.apellido} ({self.dui})'

    @property
    def nombre_completo(self):
        return f'{self.nombre} {self.apellido}'

    @property
    def is_active(self):
        return self.activo

    @is_active.setter
    def is_active(self, value):
        self.activo = value

    @property
    def is_cliente(self):
        return hasattr(self, 'cliente')

    @property
    def is_mecanico(self):
        return hasattr(self, 'mecanico')

    @property
    def is_admin(self):
        return self.is_staff and not self.is_cliente and not self.is_mecanico

    @property
    def rol(self):
        if self.is_cliente:
            return 'cliente'
        if self.is_mecanico:
            return 'mecanico'
        if self.is_admin:
            return 'admin'
        return 'sin_rol'


class Cliente(Usuario):
    """Usuario que puede registrarse y agendar sus propias citas."""

    direccion = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'


class Mecanico(Usuario):
    """Usuario interno del taller que atiende citas asignadas."""

    ESPECIALIDAD_MECANICA_GENERAL = 'mecanica_general'
    ESPECIALIDAD_ELECTRICO = 'electrico'
    ESPECIALIDAD_MOTOR = 'motor'
    ESPECIALIDAD_SUSPENSION_FRENOS = 'suspension_frenos'

    ESPECIALIDADES = [
        (ESPECIALIDAD_MECANICA_GENERAL, 'Mecánica general'),
        (ESPECIALIDAD_ELECTRICO, 'Sistema eléctrico'),
        (ESPECIALIDAD_MOTOR, 'Motor'),
        (ESPECIALIDAD_SUSPENSION_FRENOS, 'Suspensión y frenos'),
    ]

    especialidad = models.CharField(
        max_length=50,
        choices=ESPECIALIDADES,
    )

    class Meta:
        verbose_name = 'Mecánico'
        verbose_name_plural = 'Mecánicos'
