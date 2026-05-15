"""Decoradores y mixins para restringir vistas por rol."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def _requiere_rol(rol_attr, mensaje):
    """Construye un decorador que exige autenticación y el rol indicado."""

    def decorador(view_func):
        @wraps(view_func)
        @login_required
        def envoltura(request, *args, **kwargs):
            if not getattr(request.user, rol_attr, False):
                raise PermissionDenied(mensaje)
            return view_func(request, *args, **kwargs)

        return envoltura

    return decorador


solo_cliente = _requiere_rol('is_cliente', 'Esta sección es solo para clientes.')
solo_mecanico = _requiere_rol('is_mecanico', 'Esta sección es solo para mecánicos.')
solo_admin = _requiere_rol('is_admin', 'Esta sección es solo para administradores.')


class _RolRequiredMixin:
    """Mixin base para CBVs. Define `rol_requerido` en la subclase."""

    rol_requerido = None
    mensaje_denegado = 'No tienes permiso para acceder a esta sección.'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return login_required(super().dispatch)(request, *args, **kwargs)
        if self.rol_requerido and not getattr(request.user, self.rol_requerido, False):
            raise PermissionDenied(self.mensaje_denegado)
        return super().dispatch(request, *args, **kwargs)


class SoloClienteMixin(_RolRequiredMixin):
    rol_requerido = 'is_cliente'
    mensaje_denegado = 'Esta sección es solo para clientes.'


class SoloMecanicoMixin(_RolRequiredMixin):
    rol_requerido = 'is_mecanico'
    mensaje_denegado = 'Esta sección es solo para mecánicos.'


class SoloAdminMixin(_RolRequiredMixin):
    rol_requerido = 'is_admin'
    mensaje_denegado = 'Esta sección es solo para administradores.'
