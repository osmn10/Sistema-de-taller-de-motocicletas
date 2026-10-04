from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0003_proveedor_sin_nit'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='producto',
            name='proveedor_nit_anterior',
        ),
        migrations.DeleteModel(
            name='ProveedorAnterior',
        ),
    ]
