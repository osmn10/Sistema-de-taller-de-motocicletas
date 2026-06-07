"""Modelos de la app vehiculos. SCRUM-36."""

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from apps.usuarios.models import Cliente


# validador del formato salvadoreño de placa de moto: M-####
placa_validator = RegexValidator(
    regex=r'^M-\d{4}$',
    message='Formato de placa inválido. Debe ser M-#### (ej. M-1234).',
)


class Motocicleta(models.Model):
    """Moto de un Cliente. La placa es la PK natural (en vez de un id surrogate)."""

    placa = models.CharField(
        primary_key=True,  # PK natural — no necesitamos un id autoincremental
        max_length=6,
        validators=[placa_validator],
        help_text='Formato: M-####',
    )
    cliente = models.ForeignKey(
        Cliente,
        # PROTECT: si alguien intenta borrar un cliente con motos registradas, Django bloquea el delete
        on_delete=models.PROTECT,
        related_name='motocicletas',  # cliente.motocicletas.all()
    )
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    # `anio` y no `año` — la ñ da problemas en queries / migraciones de Django
    anio = models.IntegerField(
        validators=[MinValueValidator(1980)],
        help_text='Año de fabricación.',
    )
    color = models.CharField(max_length=30)
    kilometraje = models.PositiveIntegerField(default=0)
    # soft delete: nunca borramos físicamente, solo marcamos inactivo
    activo = models.BooleanField(
        default=True,
        help_text='Marcar como inactiva en lugar de eliminar.',
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Motocicleta'
        verbose_name_plural = 'Motocicletas'
        ordering = ['-fecha_registro']  # más recientes arriba

    def __str__(self):
        return f'{self.placa} · {self.marca} {self.modelo}'
