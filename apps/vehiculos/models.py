"""Modelos de la app vehiculos."""

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from apps.usuarios.models import Cliente


placa_validator = RegexValidator(
    regex=r'^M-\d{4}$',
    message='Formato de placa inválido. Debe ser M-#### (ej. M-1234).',
)


class Motocicleta(models.Model):
    """Motocicleta de un Cliente. La placa es la PK."""

    placa = models.CharField(
        primary_key=True,
        max_length=6,
        validators=[placa_validator],
        help_text='Formato: M-####',
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='motocicletas',
    )
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    anio = models.IntegerField(
        validators=[MinValueValidator(1980)],
        help_text='Año de fabricación.',
    )
    color = models.CharField(max_length=30)
    kilometraje = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(
        default=True,
        help_text='Marcar como inactiva en lugar de eliminar.',
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Motocicleta'
        verbose_name_plural = 'Motocicletas'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f'{self.placa} · {self.marca} {self.modelo}'
