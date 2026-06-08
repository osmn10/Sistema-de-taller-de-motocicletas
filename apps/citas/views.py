"""Vistas de la app citas."""

from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.configuracion.models import HorarioTaller
from apps.servicios.models import Servicio
from apps.usuarios.models import Mecanico
from apps.vehiculos.models import Motocicleta

from .models import Cita, CambioEstadoCita, ServicioCita


@login_required(login_url='usuarios:login')
def mis_citas(request):
    if not request.user.is_cliente:
        messages.error(request, 'Solo los clientes pueden ver sus citas.')
        return redirect('core:home')

    hoy = date.today()
    citas = Cita.objects.filter(
        cliente=request.user.cliente,
    ).prefetch_related('servicios').order_by('-fecha', '-hora')

    activas = [c for c in citas if c.estado != Cita.ESTADO_CANCELADA]
    canceladas = [c for c in citas if c.estado == Cita.ESTADO_CANCELADA]

    return render(request, 'citas/mis_citas.html', {
        'activas': activas,
        'canceladas': canceladas,
    })


@login_required(login_url='usuarios:login')
def reagendar_cita(request, cita_id):
    """SCRUM-35. Mueve una cita del cliente a otra fecha/hora disponible."""
    if not request.user.is_cliente:
        messages.error(request, 'Solo los clientes pueden reagendar citas.')
        return redirect('core:home')

    cita = get_object_or_404(Cita, id=cita_id, cliente=request.user.cliente)

    if not cita.puede_cancelarse():
        messages.error(request, 'Esta cita ya no se puede reagendar.')
        return redirect('citas:mis_citas')

    servicio = cita.servicios.first()
    if servicio is None:
        messages.error(request, 'La cita no tiene servicios asociados.')
        return redirect('citas:mis_citas')

    if request.method == 'POST':
        fecha_str = request.POST.get('fecha', '').strip()
        hora_str = request.POST.get('hora', '').strip()
        try:
            nueva_fecha = date.fromisoformat(fecha_str)
            nueva_hora = datetime.strptime(hora_str, '%H:%M').time()
        except ValueError:
            messages.error(request, 'Datos inválidos. Elegí un horario de la lista.')
            return redirect('citas:reagendar_cita', cita_id=cita.id)

        if nueva_fecha < date.today():
            messages.error(request, 'No podés reagendar a una fecha pasada.')
            return redirect('citas:reagendar_cita', cita_id=cita.id)

        capacidad = Mecanico.objects.filter(activo=True).count()
        ocupados = Cita.objects.filter(
            fecha=nueva_fecha,
            hora=nueva_hora,
            estado__in=[Cita.ESTADO_PENDIENTE, Cita.ESTADO_CONFIRMADA],
        ).exclude(id=cita.id).count()
        if ocupados >= capacidad:
            messages.error(request, 'Ese horario se acaba de llenar. Elegí otro.')
            url = reverse('citas:reagendar_cita', args=[cita.id])
            return redirect(f'{url}?fecha={nueva_fecha.isoformat()}')

        cita.fecha = nueva_fecha
        cita.hora = nueva_hora
        cita.save()
        messages.success(
            request,
            f'Cita #{cita.id} reagendada para el {nueva_fecha} a las {nueva_hora.strftime("%H:%M")}.',
        )
        return redirect('citas:mis_citas')

    fecha_str = request.GET.get('fecha', '').strip()
    contexto = {
        'cita': cita,
        'servicio': servicio,
        'hoy': date.today().isoformat(),
        'fecha_str': fecha_str,
    }

    if not fecha_str:
        return render(request, 'citas/reagendar_cita.html', contexto)

    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        contexto['error'] = 'Fecha inválida.'
        return render(request, 'citas/reagendar_cita.html', contexto)

    if fecha < date.today():
        contexto['error'] = 'No se pueden consultar fechas pasadas.'
        return render(request, 'citas/reagendar_cita.html', contexto)

    horario = HorarioTaller.objects.filter(dia_semana=fecha.weekday()).first()
    if not horario or not horario.abierto or not horario.hora_apertura or not horario.hora_cierre:
        contexto['mensaje'] = 'El taller no atiende ese día. Elegí otra fecha.'
        contexto['fecha'] = fecha
        return render(request, 'citas/reagendar_cita.html', contexto)

    capacidad = Mecanico.objects.filter(activo=True).count()
    if capacidad == 0:
        contexto['error'] = 'No hay mecánicos disponibles. Contactá al administrador.'
        contexto['fecha'] = fecha
        return render(request, 'citas/reagendar_cita.html', contexto)

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
        ).exclude(id=cita.id).count()
        slots.append({
            'hora': hora_slot,
            'libre': ocupados < capacidad,
        })
        actual += duracion

    contexto.update({'fecha': fecha, 'slots': slots})
    return render(request, 'citas/reagendar_cita.html', contexto)


@login_required(login_url='usuarios:login')
def cita_detalle(request, cita_id):
    if not request.user.is_cliente:
        messages.error(request, 'Solo los clientes pueden ver el detalle de sus citas.')
        return redirect('core:home')
    cita = get_object_or_404(Cita, id=cita_id, cliente=request.user.cliente)
    servicios = cita.serviciocita_set.select_related('servicio').all()
    return render(request, 'citas/cita_detalle.html', {
        'cita': cita,
        'servicios': servicios,
    })


@login_required(login_url='usuarios:login')
def cancelar_cita(request, cita_id):
    if not request.user.is_cliente:
        messages.error(request, 'Solo los clientes pueden cancelar sus citas.')
        return redirect('core:home')
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
    """
    Calendario de citas para el admin con tres modos: día, semana y mes (PBI-23).
    Permite navegar y filtrar por mecánico o estado.
    """
    if not request.user.is_admin:
        messages.error(request, 'Solo el administrador puede ver el calendario.')
        return redirect('core:home')

    import calendar as cal
    from datetime import timedelta, date, datetime
    from apps.usuarios.models import Mecanico

    modo = request.GET.get('modo', 'semana')
    if modo not in ('dia', 'semana', 'mes'):
        modo = 'semana'

    fecha_str = request.GET.get('fecha', '')
    if fecha_str:
        try:
            fecha_base = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_base = date.today()
    else:
        fecha_base = date.today()

    filtro_mecanico = request.GET.get('mecanico', '')
    filtro_estado = request.GET.get('estado', '')

    def consultar(desde, hasta):
        citas = Cita.objects.filter(
            fecha__gte=desde, fecha__lte=hasta,
        ).select_related('cliente', 'motocicleta', 'mecanico').order_by('fecha', 'hora')
        if filtro_mecanico:
            citas = citas.filter(mecanico__dui=filtro_mecanico)
        if filtro_estado:
            citas = citas.filter(estado=filtro_estado)
        return citas

    hoy = date.today()
    nombres_dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

    contexto = {
        'modo': modo,
        'fecha_base': fecha_base,
        'mecanicos': Mecanico.objects.filter(activo=True),
        'estados': Cita.ESTADOS,
        'filtro_mecanico': filtro_mecanico,
        'filtro_estado': filtro_estado,
    }

    if modo == 'dia':
        citas = consultar(fecha_base, fecha_base)
        contexto.update({
            'citas_dia': citas,
            'fecha_anterior': fecha_base - timedelta(days=1),
            'fecha_siguiente': fecha_base + timedelta(days=1),
            'es_hoy': fecha_base == hoy,
        })

    elif modo == 'mes':
        primero = fecha_base.replace(day=1)
        ultimo = fecha_base.replace(day=cal.monthrange(fecha_base.year, fecha_base.month)[1])
        citas = consultar(primero, ultimo)
        inicio_grilla = primero - timedelta(days=primero.weekday())
        fin_grilla = ultimo + timedelta(days=6 - ultimo.weekday())
        semanas = []
        dia = inicio_grilla
        while dia <= fin_grilla:
            fila = []
            for _ in range(7):
                fila.append({
                    'fecha': dia,
                    'citas': [c for c in citas if c.fecha == dia],
                    'es_hoy': dia == hoy,
                    'del_mes': dia.month == fecha_base.month,
                })
                dia += timedelta(days=1)
            semanas.append(fila)
        contexto.update({
            'semanas': semanas,
            'nombres_dias': nombres_dias,
            'mes_actual': primero,
            'fecha_anterior': (primero - timedelta(days=1)).replace(day=1),
            'fecha_siguiente': ultimo + timedelta(days=1),
        })

    else:  # semana
        lunes = fecha_base - timedelta(days=fecha_base.weekday())
        domingo = lunes + timedelta(days=6)
        citas = consultar(lunes, domingo)
        dias_semana = []
        for i in range(7):
            d = lunes + timedelta(days=i)
            dias_semana.append({
                'nombre': nombres_dias[i],
                'fecha': d,
                'citas': [c for c in citas if c.fecha == d],
                'es_hoy': d == hoy,
            })
        contexto.update({
            'dias_semana': dias_semana,
            'lunes': lunes,
            'domingo': domingo,
            'fecha_anterior': lunes - timedelta(days=7),
            'fecha_siguiente': lunes + timedelta(days=7),
        })

    return render(request, 'citas/calendario.html', contexto)


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
        'opciones_estado': [(c, dict(Cita.ESTADOS)[c]) for c in estados_posibles],
    })


@login_required(login_url='usuarios:login')
def mis_citas_mecanico(request):
    if not request.user.is_mecanico:
        messages.error(request, 'Solo los mecánicos pueden ver esta sección.')
        return redirect('core:home')

    dia_str = request.GET.get('dia', '').strip()
    estado_filtro = request.GET.get('estado', '').strip()

    citas = Cita.objects.select_related('cliente', 'motocicleta').prefetch_related('servicios')

    dia = None
    if dia_str:
        try:
            dia = date.fromisoformat(dia_str)
        except ValueError:
            dia = None

    if dia:
        citas = citas.filter(fecha=dia)
    else:
        hoy = date.today()
        citas = citas.filter(fecha__gte=hoy, fecha__lte=hoy + timedelta(days=6))

    if estado_filtro:
        citas = citas.filter(estado=estado_filtro)

    citas = citas.order_by('fecha', 'hora')

    return render(request, 'citas/mis_citas_mecanico.html', {
        'citas': citas,
        'dia_str': dia_str,
        'estado_filtro': estado_filtro,
        'estados': Cita.ESTADOS,
    })