from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Cliente, Mecanico, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Administración de usuarios sin subclase (incluye administradores)."""

    model = Usuario
    ordering = ('apellido', 'nombre')
    list_display = ('dui', 'nombre', 'apellido', 'email', 'is_staff', 'activo')
    list_filter = ('is_staff', 'is_superuser', 'activo')
    search_fields = ('dui', 'nombre', 'apellido', 'email')

    fieldsets = (
        (None, {'fields': ('dui', 'password')}),
        ('Información personal', {
            'fields': ('nombre', 'apellido', 'email', 'telefono'),
        }),
        ('Permisos', {
            'fields': (
                'activo', 'is_staff', 'is_superuser', 'groups', 'user_permissions',
            ),
        }),
        ('Fechas', {'fields': ('last_login', 'fecha_registro')}),
    )
    readonly_fields = ('fecha_registro', 'last_login')

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'dui', 'nombre', 'apellido', 'email', 'telefono',
                'password1', 'password2', 'is_staff',
            ),
        }),
    )


@admin.register(Cliente)
class ClienteAdmin(UserAdmin):
    model = Cliente
    ordering = ('apellido', 'nombre')
    list_display = ('dui', 'nombre', 'apellido', 'email', 'direccion', 'activo')
    list_filter = ('activo',)
    search_fields = ('dui', 'nombre', 'apellido', 'email')

    fieldsets = (
        (None, {'fields': ('dui', 'password')}),
        ('Información personal', {
            'fields': ('nombre', 'apellido', 'email', 'telefono', 'direccion'),
        }),
        ('Permisos', {'fields': ('activo',)}),
        ('Fechas', {'fields': ('last_login', 'fecha_registro')}),
    )
    readonly_fields = ('fecha_registro', 'last_login')

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'dui', 'nombre', 'apellido', 'email', 'telefono', 'direccion',
                'password1', 'password2',
            ),
        }),
    )


@admin.register(Mecanico)
class MecanicoAdmin(UserAdmin):
    model = Mecanico
    ordering = ('apellido', 'nombre')
    list_display = ('dui', 'nombre', 'apellido', 'email', 'especialidad', 'activo')
    list_filter = ('especialidad', 'activo')
    search_fields = ('dui', 'nombre', 'apellido', 'email')

    fieldsets = (
        (None, {'fields': ('dui', 'password')}),
        ('Información personal', {
            'fields': ('nombre', 'apellido', 'email', 'telefono'),
        }),
        ('Información laboral', {'fields': ('especialidad',)}),
        ('Permisos', {'fields': ('activo',)}),
        ('Fechas', {'fields': ('last_login', 'fecha_registro')}),
    )
    readonly_fields = ('fecha_registro', 'last_login')

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'dui', 'nombre', 'apellido', 'email', 'telefono',
                'especialidad', 'password1', 'password2',
            ),
        }),
    )
