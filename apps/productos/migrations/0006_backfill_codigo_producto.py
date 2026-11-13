from django.db import migrations


def asignar_codigos(apps, schema_editor):
    """A los productos que ya existían antes de este campo les asigna un código generado (PROD-0001, PROD-0002, ...) para que ninguno quede sin código."""
    Producto = apps.get_model('productos', 'Producto')
    for producto in Producto.objects.filter(codigo='').order_by('id'):
        producto.codigo = f'PROD-{producto.id:04d}'
        producto.save(update_fields=['codigo'])


def revertir(apps, schema_editor):
    # No hay nada que revertir: los códigos generados se quedan tal cual.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0005_producto_codigo'),
    ]

    operations = [
        migrations.RunPython(asignar_codigos, revertir),
    ]
