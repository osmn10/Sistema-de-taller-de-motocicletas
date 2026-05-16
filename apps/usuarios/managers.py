"""Managers personalizados para los modelos de usuario."""

from django.contrib.auth.base_user import BaseUserManager


class UsuarioManager(BaseUserManager):
    """Manager del modelo Usuario con métodos específicos por rol."""

    use_in_migrations = True

    def _create_user(self, dui, password, **extra_fields):
        if not dui:
            raise ValueError('El usuario debe tener un DUI.')

        email = extra_fields.get('email')
        if email:
            extra_fields['email'] = self.normalize_email(email)

        usuario = self.model(dui=dui, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, dui, password=None, **extra_fields):
        """Crea un usuario genérico sin permisos especiales ni rol asignado."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('activo', True)
        return self._create_user(dui, password, **extra_fields)

    def create_admin(self, dui, password=None, **extra_fields):
        """Crea un administrador: usuario con is_staff=True, sin subclase Cliente/Mecánico."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('activo', True)
        return self._create_user(dui, password, **extra_fields)

    def create_superuser(self, dui, password=None, **extra_fields):
        """Crea un superusuario para el comando `manage.py createsuperuser`."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('activo', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Un superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Un superusuario debe tener is_superuser=True.')

        return self._create_user(dui, password, **extra_fields)

    def create_cliente(self, dui, password=None, *, direccion='', **extra_fields):
        """Crea un Cliente (subclase de Usuario con dirección)."""
        from .models import Cliente

        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('activo', True)

        email = extra_fields.get('email')
        if email:
            extra_fields['email'] = self.normalize_email(email)

        cliente = Cliente(dui=dui, direccion=direccion, **extra_fields)
        cliente.set_password(password)
        cliente.save(using=self._db)
        return cliente

    def create_mecanico(self, dui, password=None, *, especialidad, **extra_fields):
        """Crea un Mecánico (subclase de Usuario con especialidad)."""
        from .models import Mecanico

        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('activo', True)

        email = extra_fields.get('email')
        if email:
            extra_fields['email'] = self.normalize_email(email)

        mecanico = Mecanico(dui=dui, especialidad=especialidad, **extra_fields)
        mecanico.set_password(password)
        mecanico.save(using=self._db)
        return mecanico
