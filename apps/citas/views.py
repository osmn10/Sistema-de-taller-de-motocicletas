"""Vistas de la app citas."""

from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.configuracion.models import HorarioTaller
from apps.servicios.models import Servicio
from apps.usuarios.models import Mecanico
from apps.vehiculos.models import Motocicleta

from .models import Cita, ServicioCita


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
    # solo cliente y admin: el mecánico no agenda
    if not (request.user.is_cliente or request.user.is_admin):
        messages.error(request, 'No tenés permiso para ver la disponibilidad.')
        return redirect('core:home')

    servicios = Servicio.objects.filter(activo=True).order_by('nombre')

    # GET con params del form: ?fecha=YYYY-MM-DD&servicio=ID
    fecha_str = request.GET.get('fecha', '').strip()
    servicio_id = request.GET.get('servicio', '').strip()

    # contexto base — sirve para el primer GET (sin params) y para los errores
    contexto = {
        'servicios': servicios,
        'fecha_str': fecha_str,
        'servicio_id': servicio_id,
        'hoy': date.today().isoformat(),  # para el atributo min del <input type="date">
    }

    # primera carga: solo el form vacío
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

    # weekday(): 0=Lun ... 6=Dom — coincide con los choices de HorarioTaller
    weekday = fecha.weekday()
    horario = HorarioTaller.objects.filter(dia_semana=weekday).first()
    if not horario:
        contexto['error'] = 'No hay horario configurado para ese día. Contactá al administrador.'
        contexto['fecha'] = fecha
        contexto['servicio'] = servicio
        return render(request, 'citas/disponibilidad.html', contexto)

    # taller cerrado ese día (ej. domingo)
    if not horario.abierto or not horario.hora_apertura or not horario.hora_cierre:
        contexto['mensaje'] = f'El taller no atiende los {horario.get_dia_semana_display().lower()}.'
        contexto['fecha'] = fecha
        contexto['servicio'] = servicio
        return render(request, 'citas/disponibilidad.html', contexto)

    # cuántas citas en paralelo soporta el taller en un slot = mecánicos activos
    capacidad = Mecanico.objects.filter(activo=True).count()
    if capacidad == 0:
        contexto['error'] = 'No hay mecánicos disponibles. Contactá al administrador.'
        contexto['fecha'] = fecha
        contexto['servicio'] = servicio
        return render(request, 'citas/disponibilidad.html', contexto)

    # generación de slots: del horario de apertura al de cierre, cada N min según el servicio
    duracion = timedelta(minutes=servicio.duracion_estimada)
    inicio = datetime.combine(fecha, horario.hora_apertura)
    fin = datetime.combine(fecha, horario.hora_cierre)

    slots = []
    actual = inicio
    while actual + duracion <= fin:
        hora_slot = actual.time()
        # ocupación del slot: solo cuentan citas pendientes y confirmadas
        # (las completadas/canceladas no bloquean)
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

    # ojo: request.user es Usuario base; .cliente baja a la subclase (herencia multi-tabla)
    cliente = request.user.cliente
    motos = cliente.motocicletas.filter(activo=True).order_by('-fecha_registro')
    servicios_activos = Servicio.objects.filter(activo=True).order_by('nombre')

    # sin motos no hay nada que agendar — lo mandamos a registrar una
    if not motos.exists():
        messages.warning(request, 'Necesitás registrar una motocicleta antes de agendar.')
        return redirect('vehiculos:moto_crear')

    # los 3 params vienen del botón "Agendar" de la página de disponibilidad
    fecha_str = request.GET.get('fecha', '').strip()
    hora_str = request.GET.get('hora', '').strip()
    servicio_id_str = request.GET.get('servicio', '').strip()

    # si entran directo a /agendar/ sin pasar por disponibilidad, los redirigimos
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

    # servicios que NO son el principal — se ofrecen como extras opcionales
    servicios_adicionales = servicios_activos.exclude(id=servicio_principal.id)

    if request.method == 'POST':
        moto_placa = request.POST.get('motocicleta', '').strip()
        servicios_extra_ids = request.POST.getlist('servicios_extra')  # getlist para checkboxes múltiples
        observaciones = request.POST.get('observaciones', '').strip()

        errores = {}

        # filtramos motos del cliente con .get(): si alguien manipula el form
        # mandando una placa ajena, lanza DoesNotExist y queda como error
        try:
            moto = motos.get(placa=moto_placa)
        except Motocicleta.DoesNotExist:
            errores['motocicleta'] = 'Elegí una de tus motocicletas.'
            moto = None

        # revalidamos el slot acá por si otro cliente lo agendó mientras este llenaba el form
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

        # cita queda en estado PENDIENTE y sin mecánico — el admin lo asigna después
        cita = Cita.objects.create(
            cliente=cliente,
            motocicleta=moto,
            fecha=fecha,
            hora=hora,
            observaciones=observaciones,
        )

        # snapshot del precio: si después se sube el precio_base del servicio,
        # esta cita conserva el precio que el cliente vio al agendar
        ServicioCita.objects.create(
            cita=cita,
            servicio=servicio_principal,
            precio_final=servicio_principal.precio_base,
        )
        for extra_id in servicios_extra_ids:
            try:
                extra = Servicio.objects.get(id=extra_id, activo=True)
            except Servicio.DoesNotExist:
                continue  # si alguien manda un id basura lo saltamos sin romper
            ServicioCita.objects.create(
                cita=cita,
                servicio=extra,
                precio_final=extra.precio_base,
            )

        messages.success(request, f'Cita #{cita.id} agendada para el {fecha} a las {hora.strftime("%H:%M")}.')
        return redirect('citas:cita_detalle', cita_id=cita.id)

    # GET: primera carga del form ya con fecha/hora/servicio resueltos
    return render(request, 'citas/agendar_cita.html', {
        'motos': motos,
        'fecha': fecha,
        'hora': hora,
        'servicio_principal': servicio_principal,
        'servicios_adicionales': servicios_adicionales,
        # si tiene una sola moto la dejamos preseleccionada
        'form_motocicleta': motos.first().placa if motos.count() == 1 else '',
        'form_servicios_extra': [],
        'form_observaciones': '',
    })


@login_required(login_url='usuarios:login')
def calendario(request):
    return render(request, 'citas/calendario.html')


@login_required(login_url='usuarios:login')
def mis_citas_mecanico(request):
    return render(request, 'citas/mis_citas_mecanico.html')
