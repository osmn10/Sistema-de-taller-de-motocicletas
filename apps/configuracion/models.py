"""Modelos de la app configuracion."""

from django.db import models


class HorarioTaller(models.Model):
    """Horario de atención del taller para un día de la semana.

    Existe un registro por cada día (lunes a domingo). Si `abierto` es
    False, ese día no permite agendar citas y las horas quedan vacías.
    """

    LUNES = 0
    MARTES = 1
    MIERCOLES = 2
    JUEVES = 3
    VIERNES = 4
    SABADO = 5
    DOMINGO = 6

    DIAS_SEMANA = [
        (LUNES, 'Lunes'),
        (MARTES, 'Martes'),
        (MIERCOLES, 'Miércoles'),
        (JUEVES, 'Jueves'),
        (VIERNES, 'Viernes'),
        (SABADO, 'Sábado'),
        (DOMINGO, 'Domingo'),
    ]

    dia_semana = models.IntegerField(
        choices=DIAS_SEMANA,
        unique=True,
        verbose_name='Día de la semana',
    )
    abierto = models.BooleanField(
        default=True,
        verbose_name='Atiende',
        help_text='Si el taller atiende este día.',
    )
    hora_apertura = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de apertura',
    )
    hora_cierre = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de cierre',
    )

    class Meta:
        verbose_name = 'Horario del taller'
        verbose_name_plural = 'Horarios del taller'
        ordering = ['dia_semana']

    def __str__(self):
        return self.get_dia_semana_display()