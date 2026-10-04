"""Modelos de la app citas."""

from django.db import models
from django.db.models import Case, IntegerField, When

from apps.usuarios.models import Cliente, Mecanico
from apps.vehiculos.models import Motocicleta
from apps.servicios.models import Servicio
from apps.productos.models import Producto


class EstadoCita(models.Model):
    """Estado configurable de una cita. El tipo define cómo lo trata el sistema."""

    TIPO_INICIO     = 'inicio'
    TIPO_PROCESO    = 'proceso'
    TIPO_COMPLETADO = 'completado'
    TIPO_CANCELADO  = 'cancelado'

    TIPOS = [
        (TIPO_INICIO,     'Inicio'),
        (TIPO_PROCESO,    'Proceso'),
        (TIPO_COMPLETADO, 'Finalización – completado'),
        (TIPO_CANCELADO,  'Finalización – cancelado'),
    ]

    # color automático del badge según el tipo (Confirmada conserva su azul de la migración)
    COLORES = {
        TIPO_INICIO:     '#ffb000',
        TIPO_PROCESO:    '#c084fc',
        TIPO_COMPLETADO: '#00ff66',
        TIPO_CANCELADO:  '#ff3b5c',
    }

    codigo = models.CharField(max_length=30, primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    tipo   = models.CharField(max_length=20, choices=TIPOS, default=TIPO_PROCESO)
    color  = models.CharField(max_length=7, default='#c084fc')
    orden  = models.PositiveIntegerField(default=0, help_text='Se asigna solo al crear el estado.')
    permite_cancelar = models.BooleanField(
        default=False,
        help_text='El cliente puede cancelar o reagendar la cita mientras esté en este estado.',
    )
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Estado de cita'
        verbose_name_plural = 'Estados de cita'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre

    @property
    def es_final(self):
        return self.tipo in [self.TIPO_COMPLETADO, self.TIPO_CANCELADO]

    def siguientes_posibles(self):
        """Estados a los que puede pasar una cita desde este. El flujo es fijo por tipo:

        Inicio → primer estado de Proceso (Confirmada) → otros estados de Proceso → Completado.
        Cancelado está disponible desde cualquier estado que no sea final.
        """
        activos = EstadoCita.objects.filter(activo=True)
        procesos = activos.filter(tipo=self.TIPO_PROCESO)
        primer_proceso = procesos.first()
        codigo_primer_proceso = primer_proceso.codigo if primer_proceso else None

        if self.tipo == self.TIPO_INICIO:
            codigos = [codigo_primer_proceso] if primer_proceso else []
        elif self.tipo == self.TIPO_PROCESO:
            codigos = list(
                procesos.exclude(codigo=self.codigo)
                .exclude(codigo=codigo_primer_proceso)
                .values_list('codigo', flat=True)
            )
            if self.codigo != codigo_primer_proceso:
                codigos += list(activos.filter(tipo=self.TIPO_COMPLETADO).values_list('codigo', flat=True))
        else:
            return EstadoCita.objects.none()

        codigos += list(activos.filter(tipo=self.TIPO_CANCELADO).values_list('codigo', flat=True))
        # en el desplegable van primero los de proceso, después finalizar y al final cancelar
        return activos.filter(codigo__in=codigos).order_by(
            Case(
                When(tipo=self.TIPO_PROCESO, then=0),
                When(tipo=self.TIPO_COMPLETADO, then=1),
                default=2,
                output_field=IntegerField(),
            ),
            'orden',
        )

    @property
    def color_rgb(self):
        """Color en formato 'r, g, b' para el brillo del badge (variable --sb-rgb)."""
        try:
            return ', '.join(str(int(self.color[i:i + 2], 16)) for i in (1, 3, 5))
        except ValueError:
            return '192, 132, 252'


def estado_inicial():
    """Código del estado de tipo Inicio; es el que recibe toda cita nueva."""
    return EstadoCita.objects.filter(tipo=EstadoCita.TIPO_INICIO).values_list('codigo', flat=True).first()


class Cita(models.Model):
    """Cita agendada por un cliente."""

    cliente      = models.ForeignKey(Cliente,      on_delete=models.PROTECT, related_name='citas')
    motocicleta  = models.ForeignKey(Motocicleta,  on_delete=models.PROTECT, related_name='citas')
    mecanico     = models.ForeignKey(Mecanico,     on_delete=models.PROTECT, related_name='citas', null=True, blank=True)
    servicios    = models.ManyToManyField(Servicio, through='ServicioCita', related_name='citas')
    fecha        = models.DateField()
    hora         = models.TimeField()
    estado       = models.ForeignKey(EstadoCita,   on_delete=models.PROTECT, related_name='citas', default=estado_inicial)
    observaciones = models.TextField(blank=True)
    observaciones_cierre = models.TextField(
        blank=True,
        verbose_name='Observaciones de cierre',
        help_text='Notas del administrador al finalizar el servicio (V2SCRUM-24).',
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ['-fecha', '-hora']

    def __str__(self):
        return f'Cita #{self.id} — {self.cliente} — {self.fecha}'

    def puede_cancelarse(self):
        """Depende de lo que el admin configuró en el estado actual."""
        return self.estado.permite_cancelar

    def puede_reagendarse(self):
        """Mismas condiciones que cancelar."""
        return self.estado.permite_cancelar


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
    estado_anterior = models.ForeignKey(EstadoCita, on_delete=models.PROTECT, related_name='cambios_desde')
    estado_nuevo = models.ForeignKey(EstadoCita, on_delete=models.PROTECT, related_name='cambios_hacia')
    motivo = models.TextField(blank=True)
    realizado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.PROTECT, related_name='cambios_estado')
    fecha_cambio = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_cambio']
        verbose_name = 'Cambio de estado'
        verbose_name_plural = 'Cambios de estado'

    def __str__(self):
        return f'Cita #{self.cita.id}: {self.estado_anterior} -> {self.estado_nuevo}'


class RepuestoUsado(models.Model):
    """Repuesto/producto de inventario consumido al finalizar el servicio de una cita.

    V2SCRUM-24: registra qué y cuánto se usó, y sirve de base para descontar
    el stock del producto correspondiente al finalizar la cita.
    """

    cita = models.ForeignKey(Cita, on_delete=models.PROTECT, related_name='repuestos_usados')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='usos_en_citas')
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text='Precio aplicado al cerrar. Vacío en consumos anteriores sin precio histórico.',
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('cita', 'producto')]
        verbose_name = 'Repuesto usado'
        verbose_name_plural = 'Repuestos usados'

    def __str__(self):
        return f'{self.cantidad} x {self.producto.nombre} — Cita #{self.cita.id}'
