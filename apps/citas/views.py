"""Vistas de la app citas."""

from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.configuracion.models import HorarioTaller
from apps.servicios.models import Servicio
from apps.usuarios.models import Mecanico
from apps.vehiculos.models import Motocicleta

from .models import Cita, CambioEstadoCita, ServicioCita


@login_required(login_url='usuarios:login')
def mis_citas(request):
    citas = Cita.objects.filter(
        cliente=request.user.cliente,
    ).exclude(estado=Cita.ESTADO_CANCELADA).order_by('-fecha', '-hora')
    return render(request, 'citas/mis_citas.html', {'citas': citas})


@login_required(login_url='usuarios:login')
def cita_detalle(request, cita_id):
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
def disponibilidad(request):
    """SCRUM-33. Muestra al cliente/admin los horarios libres del taller para una fecha y servicio."""
    if not (request.user.is_cliente or request.user.is_admin):
        messages.error(request, 'No tenés permiso para ver la disponibilidad.')
        return redirect('core:home')

    servicios = Servicio.objects.filter(activo=True).order_by('nombre')
    fecha_str = request.GET.get('fecha', '').strip()
    servicio_id = request.GET.get('servicio', '').strip()

    contexto = {
        'servicios': servicios,
        'fecha_str': fecha_str,
        'servicio_id': servicio_id,
        'hoy': date.today().isoformat(),
    }

    if not fecha_str or not servicio_id:
        return render(request, 'citas/disponibilidad.html', contexto)

    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        contexto['error'] = 'Fecha inválida.'
        return render(request, 'citas/disponibilidad.html', contexto)

    if fecha < date.today():
        contexto['error'] = 'No se pueden consultar fechas pasadas.'
        return render(request, 'citas/disponibilidad.html', contexto)

    try:
        servicio = Servicio.objects.get(id=servicio_id, activo=True)
    except (Servicio.DoesNotExist, ValueError):
        contexto['error'] = 'Servicio inválido.'
        return render(request, 'citas/disponibilidad.html', contexto)

    weekday = fecha.weekday()
    horario = HorarioTaller.objects.filter(dia_semana=weekday).first()
    if not horario:
        contexto['error'] = 'No hay horario configurado para ese día. Contactá al administrador.'
        contexto['fecha'] = fecha
        contexto['servicio'] = servicio
        return render(request, 'citas/disponibilidad.html', contexto)

    if not horario.abierto or not horario.hora_apertura or not horario.hora_cierre:
        contexto['mensaje'] = f'El taller no atiende los {horario.get_dia_semana_display().lower()}.'
        contexto['fecha'] = fecha
        contexto['servicio'] = servicio
        return render(request, 'citas/disponibilidad.html', contexto)

    capacidad = Mecanico.objects.filter(activo=True).count()
    if capacidad == 0:
        contexto['error'] = 'No hay mecánicos disponibles. Contactá al administrador.'
        contexto['fecha'] = fecha
        contexto['servicio'] = servicio
        return render(request, 'citas/disponibilidad.html', contexto)

    duracion = timedelta(minutes=servicio.duracion_estimada)
    inicio = datetime.combine(fecha, horario.hora_apertura)
    fin = datetime.combine(fecha, horario.hora_cierre)

    slots = []
    actual = inicio
    while actual + duracion <= fin:
        hora_slot = actual.time()
        ocupados = Cita.objects.filter(
            fecha=fecha,
            hora=hora_slot,
            estado__in=[Cita.ESTADO_PENDIENTE, Cita.ESTADO_CONFIRMADA],
        ).count()
        slots.append({
            'hora': hora_slot,
            'ocupados': ocupados,
            'capacidad': capacidad,
            'libre': ocupados < capacidad,
        })
        actual += duracion

    contexto.update({
        'fecha': fecha,
        'servicio': servicio,
        'horario': horario,
        'slots': slots,
        'capacidad': capacidad,
    })
    return render(request, 'citas/disponibilidad.html', contexto)


@login_required(login_url='usuarios:login')
def agendar_cita(request):
    """SCRUM-41. Crea una cita nueva. Solo el cliente puede agendar (en su propio nombre)."""
    if not request.user.is_cliente:
        messages.error(request, 'Solo los clientes pueden agendar citas.')
        return redirect('core:home')

    cliente = request.user.cliente
    motos = cliente.motocicletas.filter(activo=True).order_by('-fecha_registro')
    servicios_activos = Servicio.objects.filter(activo=True).order_by('nombre')

    if not motos.exists():
        messages.warning(request, 'Necesitás registrar una motocicleta antes de agendar.')
        return redirect('vehiculos:moto_crear')

    fecha_str = request.GET.get('fecha', '').strip()
    hora_str = request.GET.get('hora', '').strip()
    servicio_id_str = request.GET.get('servicio', '').strip()

    if not fecha_str or not servicio_id_str or not hora_str:
        messages.info(request, 'Elegí primero una fecha y hora disponibles.')
        return redirect('citas:disponibilidad')

    try:
        fecha = date.fromisoformat(fecha_str)
        hora = datetime.strptime(hora_str, '%H:%M').time()
        servicio_principal = Servicio.objects.get(id=servicio_id_str, activo=True)
    except (ValueError, Servicio.DoesNotExist):
        messages.error(request, 'Parámetros inválidos. Volvé a elegir un slot disponible.')
        return redirect('citas:disponibilidad')

    if fecha < date.today():
        messages.error(request, 'No podés agendar en fechas pasadas.')
        return redirect('citas:disponibilidad')

    servicios_adicionales = servicios_activos.exclude(id=servicio_principal.id)

    if request.method == 'POST':
        moto_placa = request.POST.get('motocicleta', '').strip()
        servicios_extra_ids = request.POST.getlist('servicios_extra')
        observaciones = request.POST.get('observaciones', '').strip()
        errores = {}

        try:
            moto = motos.get(placa=moto_placa)
        except Motocicleta.DoesNotExist:
            errores['motocicleta'] = 'Elegí una de tus motocicletas.'
            moto = None

        capacidad = Mecanico.objects.filter(activo=True).count()
        ocupados = Cita.objects.filter(
            fecha=fecha,
            hora=hora,
            estado__in=[Cita.ESTADO_PENDIENTE, Cita.ESTADO_CONFIRMADA],
        ).count()
        if ocupados >= capacidad:
            errores['slot'] = 'Este horario se acaba de llenar. Elegí otro.'

        if errores:
            return render(request, 'citas/agendar_cita.html', {
                'errores': errores,
                'motos': motos,
                'fecha': fecha,
                'hora': hora,
                'servicio_principal': servicio_principal,
                'servicios_adicionales': servicios_adicionales,
                'form_motocicleta': moto_placa,
                'form_servicios_extra': servicios_extra_ids,
                'form_observaciones': observaciones,
            })

        cita = Cita.objects.create(
            cliente=cliente,
            motocicleta=moto,
            fecha=fecha,
            hora=hora,
            observaciones=observaciones,
        )
        ServicioCita.objects.create(
            cita=cita,
            servicio=servicio_principal,
            precio_final=servicio_principal.precio_base,
        )
        for extra_id in servicios_extra_ids:
            try:
                extra = Servicio.objects.get(id=extra_id, activo=True)
            except Servicio.DoesNotExist:
                continue
            ServicioCita.objects.create(
                cita=cita,
                servicio=extra,
                precio_final=extra.precio_base,
            )

        messages.success(request, f'Cita #{cita.id} agendada para el {fecha} a las {hora.strftime("%H:%M")}.')
        return redirect('citas:cita_detalle', cita_id=cita.id)

    return render(request, 'citas/agendar_cita.html', {
        'motos': motos,
        'fecha': fecha,
        'hora': hora,
        'servicio_principal': servicio_principal,
        'servicios_adicionales': servicios_adicionales,
        'form_motocicleta': motos.first().placa if motos.count() == 1 else '',
        'form_servicios_extra': [],
        'form_observaciones': '',
    })


@login_required(login_url='usuarios:login')
def calendario(request):
    """SCRUM-40. Calendario de citas para el admin con filtros."""
    if not request.user.is_admin:
        messages.error(request, 'Solo el administrador puede ver el calendario.')
        return redirect('core:home')

    hoy = date.today()
    semana_offset = int(request.GET.get('semana', 0))
    inicio_semana = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=semana_offset)
    fin_semana = inicio_semana + timedelta(days=6)

    mecanico_id = request.GET.get('mecanico', '')
    estado_filtro = request.GET.get('estado', '')

    citas = Cita.objects.filter(
        fecha__range=[inicio_semana, fin_semana]
    ).select_related('cliente', 'motocicleta', 'mecanico').order_by('fecha', 'hora')

    if mecanico_id:
        citas = citas.filter(mecanico__dui=mecanico_id)
    if estado_filtro:
        citas = citas.filter(estado=estado_filtro)

    dias = []
    for i in range(7):
        dia = inicio_semana + timedelta(days=i)
        dias.append({
            'fecha': dia,
            'citas': [c for c in citas if c.fecha == dia],
        })

    mecanicos = Mecanico.objects.filter(activo=True)

    return render(request, 'citas/calendario.html', {
        'dias': dias,
        'inicio_semana': inicio_semana,
        'fin_semana': fin_semana,
        'semana_offset': semana_offset,
        'mecanicos': mecanicos,
        'estados': Cita.ESTADOS,
        'mecanico_id': mecanico_id,
        'estado_filtro': estado_filtro,
    })


@login_required(login_url='usuarios:login')
def cita_admin_detalle(request, cita_id):
    """SCRUM-40. Detalle de cita para el admin — cambia estado con motivo."""
    if not request.user.is_admin:
        messages.error(request, 'Solo el administrador puede gestionar estados.')
        return redirect('core:home')

    cita = get_object_or_404(Cita, id=cita_id)
    servicios = cita.serviciocita_set.select_related('servicio').all()
    cambios = cita.cambios_estado.select_related('realizado_por').all()

    TRANSICIONES = {
        Cita.ESTADO_PENDIENTE:  [Cita.ESTADO_CONFIRMADA, Cita.ESTADO_CANCELADA],
        Cita.ESTADO_CONFIRMADA: [Cita.ESTADO_EN_PROCESO, Cita.ESTADO_CANCELADA],
        Cita.ESTADO_EN_PROCESO: [Cita.ESTADO_COMPLETADA, Cita.ESTADO_CANCELADA],
        Cita.ESTADO_COMPLETADA: [],
        Cita.ESTADO_CANCELADA:  [],
    }
    estados_posibles = TRANSICIONES.get(cita.estado, [])

    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado', '').strip()
        motivo = request.POST.get('motivo', '').strip()

        if nuevo_estado not in estados_posibles:
            messages.error(request, 'Transición de estado no válida.')
            return redirect('citas:cita_admin_detalle', cita_id=cita.id)

        if nuevo_estado == Cita.ESTADO_CANCELADA and not motivo:
            messages.error(request, 'El motivo es obligatorio para cancelar.')
            return redirect('citas:cita_admin_detalle', cita_id=cita.id)

        CambioEstadoCita.objects.create(
            cita=cita,
            estado_anterior=cita.estado,
            estado_nuevo=nuevo_estado,
            motivo=motivo,
            realizado_por=request.user,
        )
        cita.estado = nuevo_estado
        cita.save()
        messages.success(request, f'Cita #{cita.id} actualizada a {nuevo_estado}.')
        return redirect('citas:cita_admin_detalle', cita_id=cita.id)

    return render(request, 'citas/cita_admin_detalle.html', {
        'cita': cita,
        'servicios': servicios,
        'cambios': cambios,
        'estados_posibles': estados_posibles,
        'estados_display': dict(Cita.ESTADOS),
    })


@login_required(login_url='usuarios:login')
def mis_citas_mecanico(request):
    return render(request, 'citas/mis_citas_mecanico.html')