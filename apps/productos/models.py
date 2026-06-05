"""Modelos de la app productos."""

from django.core.validators import RegexValidator
from django.db import models


# Validador para el formato de NIT: ####-######-###-#
nit_validator = RegexValidator(
    regex=r'^\d{4}-\d{6}-\d{3}-\d$',
    message='Formato de NIT inválido. Debe ser ####-######-###-#.',
)


class Proveedor(models.Model):
    """Proveedor de productos y repuestos del taller."""

    # NIT como llave primaria con formato ####-######-###-#
    nit = models.CharField(
        primary_key=True,
        max_length=17,
        validators=[nit_validator],
        verbose_name='NIT',
        help_text='Formato: ####-######-###-#',
    )
    # Nombre o razón social del proveedor
    nombre = models.CharField(max_length=200, verbose_name='Razón social')
    # Teléfono de contacto del proveedor
    telefono = models.CharField(max_length=9, blank=True)
    # Correo electrónico del proveedor
    email = models.EmailField(blank=True)
    # Estado activo/inactivo (soft delete)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """Producto o repuesto del inventario del taller."""

    # Nombre del producto (ej: "Aceite 10W-40", "Pastilla de freno")
    nombre = models.CharField(max_length=200)
    # Descripción detallada del producto
    descripcion = models.TextField(blank=True)
    # Precio unitario del producto
    precio = models.DecimalField(max_digits=8, decimal_places=2)
    # Cantidad disponible actualmente en el inventario
    stock_actual = models.PositiveIntegerField(default=0)
    # Cantidad mínima antes de disparar alerta de stock bajo
    stock_minimo = models.PositiveIntegerField(default=5)
    # Proveedor que suministra este producto (relación muchos a uno)
    # PROTECT evita eliminar un proveedor que tiene productos asociados
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name='productos',
        null=True,
        blank=True,
    )
    # Estado activo/inactivo (soft delete: no se borra, se desactiva)
    activo = models.BooleanField(default=True)
    # Fecha en que se registró el producto
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def stock_bajo(self):
        """Retorna True si el stock actual está por debajo del mínimo."""
        return self.stock_actual < self.stock_minimo