# V2SCRUM-42: calificación del servicio recibido.

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0005_estados_cita_configurables'),
    ]

    operations = [
        migrations.CreateModel(
            name='CalificacionCita',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puntuacion', models.PositiveSmallIntegerField(help_text='De 1 a 5 estrellas.', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('comentario', models.TextField(blank=True, max_length=500)),
                ('fecha_registro', models.DateTimeField(auto_now_add=True)),
                ('cita', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='calificacion', to='citas.cita')),
            ],
            options={
                'verbose_name': 'Calificación de cita',
                'verbose_name_plural': 'Calificaciones de citas',
                'ordering': ['-fecha_registro'],
            },
        ),
    ]
