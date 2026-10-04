from django.db import migrations, models


def guardar_nit(apps, schema_editor):
    """Guarda en cada producto el NIT de su proveedor antes de cambiar la llave del proveedor."""
    Producto = apps.get_model('productos', 'Producto')
    for producto in Producto.objects.exclude(proveedor__isnull=True):
        producto.proveedor_nit_anterior = producto.proveedor_id
        producto.save(update_fields=['proveedor_nit_anterior'])


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='proveedor_nit_anterior',
            field=models.CharField(max_length=17, null=True, blank=True),
        ),
        migrations.RunPython(guardar_nit, migrations.RunPython.noop),
    ]
