"""Modelos de la app servicios."""

from django.db import models


class Servicio(models.Model):
    """Servicio del catálogo del taller."""

    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    precio_base = models.DecimalField(max_digits=8, decimal_places=2)
    duracion_estimada = models.PositiveIntegerField(help_text='Duración en minutos.')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Servicio'
        verbose_name_plural = 'Servicios'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def duracion_display(self):
        """Devuelve la duración en formato legible (ej: 30 min, 2 h)."""
        if self.duracion_estimada < 60:
            return f'{self.duracion_estimada} min'
        horas = self.duracion_estimada // 60
        minutos = self.duracion_estimada % 60
        if minutos:
            return f'{horas} h {minutos} min'
        return f'{horas} h'
