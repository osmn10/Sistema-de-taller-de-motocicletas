from django.contrib import admin

from .models import Motocicleta


@admin.register(Motocicleta)
class MotocicletaAdmin(admin.ModelAdmin):
    list_display = ('placa', 'cliente', 'marca', 'modelo', 'anio', 'kilometraje', 'activo')
    list_filter = ('activo', 'marca', 'anio')
    search_fields = ('placa', 'marca', 'modelo', 'cliente__nombre', 'cliente__apellido')
