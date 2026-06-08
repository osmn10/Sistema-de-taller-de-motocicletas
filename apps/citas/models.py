"""Modelos de la app citas."""

from django.db import models

from apps.usuarios.models import Cliente, Mecanico
from apps.vehiculos.models import Motocicleta
from apps.servicios.models import Servicio


class Cita(models.Model):
    """Cita agendada por un cliente."""

    ESTADO_PENDIENTE    = 'pendiente'
    ESTADO_CONFIRMADA   = 'confirmada'
    ESTADO_EN_PROCESO   = 'en_proceso'
    ESTADO_COMPLETADA   = 'completada'
    ESTADO_CANCELADA    = 'cancelada'

    ESTADOS = [
        (ESTADO_PENDIENTE,  'Pendiente'),
        (ESTADO_CONFIRMADA, 'Confirmada'),
        (ESTADO_EN_PROCESO, 'En proceso'),
        (ESTADO_COMPLETADA, 'Completada'),
        (ESTADO_CANCELADA,  'Cancelada'),
    ]

    cliente      = models.ForeignKey(Cliente,      on_delete=models.PROTECT, related_name='citas')
    motocicleta  = models.ForeignKey(Motocicleta,  on_delete=models.PROTECT, related_name='citas')
    mecanico     = models.ForeignKey(Mecanico,     on_delete=models.PROTECT, related_name='citas', null=True, blank=True)
    servicios    = models.ManyToManyField(Servicio, through='ServicioCita', related_name='citas')
    fecha        = models.DateField()
    hora         = models.TimeField()
    estado       = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_PENDIENTE)
    observaciones = models.TextField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ['-fecha', '-hora']

    def __str__(self):
        return f'Cita #{self.id} — {self.cliente} — {self.fecha}'

    def puede_cancelarse(self):
        """Solo se puede cancelar si está pendiente o confirmada."""
        return self.estado in [self.ESTADO_PENDIENTE, self.ESTADO_CONFIRMADA]
    
    def puede_reagendarse(self):
        """Solo se puede reagendar si está pendiente o confirmada."""
        return self.estado in [self.ESTADO_PENDIENTE, self.ESTADO_CONFIRMADA]


class ServicioCita(models.Model):
    """Association class entre Cita y Servicio."""

    cita          = models.ForeignKey(Cita,     on_delete=models.CASCADE)
    servicio      = models.ForeignKey(Servicio, on_delete=models.PROTECT)
    precio_final  = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        unique_together = [('cita', 'servicio')]
        verbose_name = 'Servicio de cita'
        verbose_name_plural = 'Servicios de cita'

    def __str__(self):
        return f'{self.servicio.nombre} — Cita #{self.cita.id}'
class CambioEstadoCita(models.Model):
    """Registra cada transición de estado de una cita."""

    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='cambios_estado')
    estado_anterior = models.CharField(max_length=20, choices=Cita.ESTADOS)
    estado_nuevo = models.CharField(max_length=20, choices=Cita.ESTADOS)
    motivo = models.TextField(blank=True)
    realizado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.PROTECT, related_name='cambios_estado')
    fecha_cambio = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_cambio']
        verbose_name = 'Cambio de estado'
        verbose_name_plural = 'Cambios de estado'

    def __str__(self):
        return f'Cita #{self.cita.id}: {self.estado_anterior} -> {self.estado_nuevo}'