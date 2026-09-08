from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('citas', '0003_cita_observaciones_cierre_repuestousado')]

    operations = [
        migrations.AddField(
            model_name='repuestousado',
            name='precio_unitario',
            field=models.DecimalField(
                max_digits=8, decimal_places=2, null=True, blank=True,
                help_text='Precio aplicado al cerrar. Vacío en consumos anteriores sin precio histórico.',
            ),
        ),
    ]
