"""Vistas de la app citas."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Cita


@login_required(login_url='usuarios:login')
def mis_citas(request):
    citas = Cita.objects.filter(
        cliente=request.user.cliente,
    ).exclude(estado=Cita.ESTADO_CANCELADA).order_by('-fecha', '-hora')
    return render(request, 'citas/mis_citas.html', {'citas': citas})


@login_required(login_url='usuarios:login')
def cita_detalle(request, cita_id):
    if request.user.is_admin:
        cita = get_object_or_404(Cita, id=cita_id)
    else:
        cita = get_object_or_404(Cita, id=cita_id, cliente=request.user.cliente)
    servicios = cita.serviciocita_set.select_related('servicio').all()
    return render(request, 'citas/cita_detalle.html', {
        'cita': cita,
        'servicios': servicios,
    })


@login_required(login_url='usuarios:login')
def cancelar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, cliente=request.user.cliente)
    if request.method == 'POST':
        if cita.puede_cancelarse():
            cita.estado = Cita.ESTADO_CANCELADA
            cita.save()
            messages.success(request, f'Cita cancelada correctamente.')
        else:
            messages.error(request, 'Esta cita no puede cancelarse.')
        return redirect('citas:mis_citas')
    return redirect('citas:cita_detalle', cita_id=cita.id)


@login_required(login_url='usuarios:login')
def calendario(request):
    """
    Muestra el calendario semanal de citas para el admin.
    Permite navegar entre semanas y filtrar por mecánico o estado.
    """
    from datetime import timedelta, date
    from apps.usuarios.models import Mecanico

    # Obtener la fecha base (hoy o la que venga por parámetro GET)
    fecha_str = request.GET.get('fecha', '')
    if fecha_str:
        try:
            from datetime import datetime
            fecha_base = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_base = date.today()
    else:
        fecha_base = date.today()

    # Calcular lunes y domingo de la semana actual
    # weekday() retorna 0=lunes, 6=domingo
    lunes = fecha_base - timedelta(days=fecha_base.weekday())
    domingo = lunes + timedelta(days=6)

    # Calcular lunes de la semana anterior y siguiente (para navegación)
    lunes_anterior = lunes - timedelta(days=7)
    lunes_siguiente = lunes + timedelta(days=7)

    # Obtener filtros opcionales
    filtro_mecanico = request.GET.get('mecanico', '')
    filtro_estado = request.GET.get('estado', '')

    # Consultar todas las citas de la semana
    citas = Cita.objects.filter(
        fecha__gte=lunes,
        fecha__lte=domingo,
    ).select_related('cliente', 'motocicleta', 'mecanico').order_by('fecha', 'hora')

    # Aplicar filtro por mecánico si se seleccionó uno
    if filtro_mecanico:
        citas = citas.filter(mecanico__dui=filtro_mecanico)

    # Aplicar filtro por estado si se seleccionó uno
    if filtro_estado:
        citas = citas.filter(estado=filtro_estado)

    # Organizar citas por día de la semana para el template
    # Crear una lista de 7 días con sus citas
    dias_semana = []
    nombres_dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    for i in range(7):
        dia = lunes + timedelta(days=i)
        citas_del_dia = [c for c in citas if c.fecha == dia]
        dias_semana.append({
            'nombre': nombres_dias[i],
            'fecha': dia,
            'citas': citas_del_dia,
            'es_hoy': dia == date.today(),
        })

    # Obtener lista de mecánicos y estados para los filtros
    mecanicos = Mecanico.objects.filter(activo=True)
    estados = Cita.ESTADOS

    return render(request, 'citas/calendario.html', {
        'dias_semana': dias_semana,
        'lunes': lunes,
        'domingo': domingo,
        'lunes_anterior': lunes_anterior,
        'lunes_siguiente': lunes_siguiente,
        'mecanicos': mecanicos,
        'estados': estados,
        'filtro_mecanico': filtro_mecanico,
        'filtro_estado': filtro_estado,
    })


@login_required(login_url='usuarios:login')
def mis_citas_mecanico(request):
    return render(request, 'citas/mis_citas_mecanico.html')


@login_required(login_url='usuarios:login')
def reagendar_cita(request, cita_id):
    """Permite al cliente cambiar la fecha y hora de una cita."""
    cita = get_object_or_404(Cita, id=cita_id, cliente=request.user.cliente)

    if not cita.puede_reagendarse():
        messages.error(request, 'Esta cita no puede reagendarse.')
        return redirect('citas:cita_detalle', cita_id=cita.id)

    if request.method == 'POST':
        nueva_fecha = request.POST.get('fecha', '').strip()
        nueva_hora = request.POST.get('hora', '').strip()

        errores = {}

        if not nueva_fecha:
            errores['fecha'] = 'La fecha es obligatoria.'
        if not nueva_hora:
            errores['hora'] = 'La hora es obligatoria.'

        fecha_obj = None
        hora_obj = None

        if nueva_fecha:
            from datetime import date, datetime
            try:
                fecha_obj = datetime.strptime(nueva_fecha, '%Y-%m-%d').date()
                if fecha_obj < date.today():
                    errores['fecha'] = 'La fecha debe ser posterior a hoy.'
                elif fecha_obj == date.today():
                    errores['fecha'] = 'No podés reagendar para el mismo día de hoy.'
            except ValueError:
                errores['fecha'] = 'Formato de fecha inválido.'

        if nueva_hora:
            from datetime import datetime
            try:
                hora_obj = datetime.strptime(nueva_hora, '%H:%M').time()
            except ValueError:
                errores['hora'] = 'Formato de hora inválido.'

        if errores:
            return render(request, 'citas/reagendar_cita.html', {
                'cita': cita,
                'errores': errores,
                'fecha': nueva_fecha,
                'hora': nueva_hora,
            })

        cita.fecha = fecha_obj
        cita.hora = hora_obj
        if cita.estado == Cita.ESTADO_CONFIRMADA:
            cita.estado = Cita.ESTADO_PENDIENTE
        cita.save()

        messages.success(request, 'Cita reagendada correctamente.')
        return redirect('citas:cita_detalle', cita_id=cita.id)

    return render(request, 'citas/reagendar_cita.html', {
        'cita': cita,
        'fecha': cita.fecha.strftime('%Y-%m-%d'),
        'hora': cita.hora.strftime('%H:%M'),
    })