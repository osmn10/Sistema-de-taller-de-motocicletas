from django.db import migrations


def cargar_transiciones(apps, schema_editor):
    """HU037: guarda como transiciones el flujo que antes estaba fijo por tipo, para todos los estados."""
    EstadoCita = apps.get_model('citas', 'EstadoCita')
    estados = list(EstadoCita.objects.order_by('orden', 'nombre'))
    procesos = [e for e in estados if e.tipo == 'proceso']
    procesos_activos = [e for e in procesos if e.activo]
    # el primer proceso (Confirmada) es el primero activo, igual que en el flujo anterior
    primer_proceso = procesos_activos[0] if procesos_activos else (procesos[0] if procesos else None)
    completados = [e for e in estados if e.tipo == 'completado']
    cancelados = [e for e in estados if e.tipo == 'cancelado']

    for estado in estados:
        if estado.tipo == 'inicio':
            destinos = ([primer_proceso] if primer_proceso else []) + cancelados
        elif estado.tipo == 'proceso':
            destinos = [p for p in procesos if p.codigo not in (estado.codigo, primer_proceso.codigo)]
            if estado.codigo != primer_proceso.codigo:
                destinos += completados
            destinos += cancelados
        else:
            destinos = []  # los estados finales no tienen salida
        estado.transiciones.set(destinos)


def borrar_transiciones(apps, schema_editor):
    EstadoCita = apps.get_model('citas', 'EstadoCita')
    EstadoCita.transiciones.through.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0007_agregar_transiciones_estado'),
    ]

    operations = [
        migrations.RunPython(cargar_transiciones, borrar_transiciones),
    ]
