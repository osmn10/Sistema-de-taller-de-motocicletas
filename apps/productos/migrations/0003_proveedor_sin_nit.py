import django.db.models.deletion
from django.db import migrations, models


def pasar_proveedores(apps, schema_editor):
    """Copia cada proveedor a la tabla nueva (con id) y vuelve a asociarle sus productos."""
    ProveedorAnterior = apps.get_model('productos', 'ProveedorAnterior')
    Proveedor = apps.get_model('productos', 'Proveedor')
    Producto = apps.get_model('productos', 'Producto')
    for anterior in ProveedorAnterior.objects.all():
        nuevo = Proveedor.objects.create(
            nombre=anterior.nombre,
            telefono=anterior.telefono,
            email=anterior.email,
            activo=anterior.activo,
        )
        Producto.objects.filter(proveedor_nit_anterior=anterior.nit).update(proveedor=nuevo)


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0002_guardar_nit_de_proveedor'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='producto',
            name='proveedor',
        ),
        migrations.RenameModel(
            old_name='Proveedor',
            new_name='ProveedorAnterior',
        ),
        migrations.CreateModel(
            name='Proveedor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200)),
                ('telefono', models.CharField(blank=True, max_length=9)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Proveedor',
                'verbose_name_plural': 'Proveedores',
                'ordering': ['nombre'],
            },
        ),
        migrations.AddField(
            model_name='producto',
            name='proveedor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='productos', to='productos.proveedor'),
        ),
        migrations.RunPython(pasar_proveedores, migrations.RunPython.noop),
    ]
