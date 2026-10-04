"""Vistas de la app citas."""

from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.configuracion.models import HorarioTaller
from apps.core.utils import rango_fechas
from apps.productos.models import Producto
from apps.servicios.models import Servicio
from apps.usuarios.models import Mecanico
from apps.vehiculos.models import Motocicleta

from .models import Cita, CambioEstadoCita, EstadoCita, RepuestoUsado, ServicioCita
from .totales import calcular_detalle_cita, precio_valido
from .reporte_excel import generar_reporte_excel
from .reporte_pdf import generar_reporte_pdf
from .reportes import calcular_reporte_servicios
from .ticket_pdf import generar_ticket_pdf
from .services import (
    cita_en_conflicto,
    mecanicos_disponibles,
    notificar_cita_agendada,
    notificar_cita_cancelada,
    notificar_cita_completada,
    notificar_cita_confirmada,
    notificar_cita_reagendada,
)


@login_required(login_url='usuarios:login')
def mis_citas(request):
    if not request.user.is_cliente:
        messages.error(request, 'Solo los clientes pueden ver sus citas.')
        return redirect('core:home')

    hoy = timezone.localdate()
    citas = Cita.objects.filter(
        cliente=request.user.cliente,
    ).select_related('estado').prefetch_related('servicios').order_by('-fecha', '-hora')

    activas = [c for c in citas if c.estado.tipo != EstadoCita.TIPO_CANCELADO]
    canceladas = [c for c in citas if c.estado.tipo == EstadoCita.TIPO_CANCELADO]

    return render(request, 'citas/mis_citas.html', {
        'activas': activas,
        'canceladas': canceladas,
    })


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
        'hoy': timezone.localdate().isoformat(),
    }

    if not fecha_str or not servicio_id:
        return render(request, 'citas/disponibilidad.html', contexto)

    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        contexto['error'] = 'Fecha inválida.'
        return render(request, 'citas/disponibilidad.html', contexto)

    if fecha < timezone.localdate():
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

    ahora = timezone.localtime()
    slots = []
    actual = inicio
    while actual + duracion <= fin:
        hora_slot = actual.time()
        # si es hoy, solo se ofrecen los horarios que todavía no empezaron
        if fecha == ahora.date() and hora_slot <= ahora.time():
            actual += duracion
            continue
        ocupados = Cita.objects.filter(
            fecha=fecha,
            hora=hora_slot,
            estado__tipo__in=[EstadoCita.TIPO_INICIO, EstadoCita.TIPO_PROCESO],
        ).count()
        slots.append({
            'hora': hora_slot,
            'ocupados': ocupados,
            'capacidad': capacidad,
            'libre': ocupados < capacidad,
        })
        actual += duracion

    if not slots:
        contexto['mensaje'] = 'Ya no hay horarios disponibles para hoy. Elegí otra fecha.'

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

    if fecha < timezone.localdate():
        messages.error(request, 'No podés agendar en fechas pasadas.')
        return redirect('citas:disponibilidad')

    ahora = timezone.localtime()
    if fecha == ahora.date() and hora <= ahora.time():
        messages.error(request, 'Ese horario ya pasó. Elegí otro.')
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
            estado__tipo__in=[EstadoCita.TIPO_INICIO, EstadoCita.TIPO_PROCESO],
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

        with transaction.atomic():
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

            transaction.on_commit(
                lambda cita_id=cita.id: notificar_cita_agendada(cita_id)
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
def cita_detalle(request, cita_id):
    if not request.user.is_cliente:
        messages.error(request, 'Solo los clientes pueden ver el detalle de sus citas.')
        return redirect('core:home')
    cita = get_object_or_404(Cita, id=cita_id, cliente=request.user.cliente)
    servicios = cita.serviciocita_set.select_related('servicio').all()
    return render(request, 'citas/cita_detalle.html', {
        'cita': cita,
        'servicios': servicios,
        'detalle_economico': (
            calcular_detalle_cita(cita) if cita.estado.tipo == EstadoCita.TIPO_COMPLETADO else None
        ),
    })


@login_required(login_url='usuarios:login')
def descargar_ticket(request, cita_id):
    """V2SCRUM-30. Descarga del ticket PDF desde el historial del cliente.

    El PDF se genera al vuelo a partir de las líneas guardadas de la cita
    (misma fuente que el correo de cierre), no se persiste en disco/BD.
    """
    if not request.user.is_cliente:
        messages.error(request, 'Solo los clientes pueden descargar su ticket.')
        return redirect('core:home')

    cita = get_object_or_404(Cita, id=cita_id, cliente=request.user.cliente)
    if cita.estado.tipo != EstadoCita.TIPO_COMPLETADO:
        messages.error(request, 'El ticket solo está disponible para citas completadas.')
        return redirect('citas:cita_detalle', cita_id=cita.id)

    detalle = calcular_detalle_cita(cita)
    if detalle['errores']:
        messages.error(request, 'No fue posible generar el ticket: ' + '; '.join(detalle['errores']))
        return redirect('citas:cita_detalle', cita_id=cita.id)

    pdf_bytes = generar_ticket_pdf(cita, detalle)
    respuesta = HttpResponse(pdf_bytes, content_type='application/pdf')
    respuesta['Content-Disposition'] = f'attachment; filename="ticket_cita_{cita.id}.pdf"'
    return respuesta


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

        if nueva_fecha < timezone.localdate():
            messages.error(request, 'No podés reagendar a una fecha pasada.')
            return redirect('citas:reagendar_cita', cita_id=cita.id)

        ahora = timezone.localtime()
        if nueva_fecha == ahora.date() and nueva_hora <= ahora.time():
            messages.error(request, 'Ese horario ya pasó. Elegí otro.')
            url = reverse('citas:reagendar_cita', args=[cita.id])
            return redirect(f'{url}?fecha={nueva_fecha.isoformat()}')

        capacidad = Mecanico.objects.filter(activo=True).count()
        ocupados = Cita.objects.filter(
            fecha=nueva_fecha,
            hora=nueva_hora,
            estado__tipo__in=[EstadoCita.TIPO_INICIO, EstadoCita.TIPO_PROCESO],
        ).exclude(id=cita.id).count()
        if ocupados >= capacidad:
            messages.error(request, 'Ese horario se acaba de llenar. Elegí otro.')
            url = reverse('citas:reagendar_cita', args=[cita.id])
            return redirect(f'{url}?fecha={nueva_fecha.isoformat()}')

        fecha_anterior = cita.fecha
        hora_anterior = cita.hora

        with transaction.atomic():
            cita.fecha = nueva_fecha
            cita.hora = nueva_hora
            cita.save()

            transaction.on_commit(
                lambda cita_id=cita.id: notificar_cita_reagendada(
                    cita_id, fecha_anterior, hora_anterior,
                )
            )

        messages.success(
            request,
            f'Cita #{cita.id} reagendada para el {nueva_fecha} a las {nueva_hora.strftime("%H:%M")}.',
        )
        return redirect('citas:mis_citas')

    fecha_str = request.GET.get('fecha', '').strip()
    contexto = {
        'cita': cita,
        'servicio': servicio,
        'hoy': timezone.localdate().isoformat(),
        'fecha_str': fecha_str,
    }

    if not fecha_str:
        return render(request, 'citas/reagendar_cita.html', contexto)

    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        contexto['error'] = 'Fecha inválida.'
        return render(request, 'citas/reagendar_cita.html', contexto)

    if fecha < timezone.localdate():
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

    ahora = timezone.localtime()
    slots = []
    actual = inicio
    while actual + duracion <= fin:
        hora_slot = actual.time()
        # si es hoy, solo se ofrecen los horarios que todavía no empezaron
        if fecha == ahora.date() and hora_slot <= ahora.time():
            actual += duracion
            continue
        ocupados = Cita.objects.filter(
            fecha=fecha,
            hora=hora_slot,
            estado__tipo__in=[EstadoCita.TIPO_INICIO, EstadoCita.TIPO_PROCESO],
        ).exclude(id=cita.id).count()
        slots.append({
            'hora': hora_slot,
            'libre': ocupados < capacidad,
        })
        actual += duracion

    if not slots:
        contexto['mensaje'] = 'Ya no hay horarios disponibles para hoy. Elegí otra fecha.'

    contexto.update({'fecha': fecha, 'slots': slots})
    return render(request, 'citas/reagendar_cita.html', contexto)

@login_required(login_url='usuarios:login')
def cancelar_cita(request, cita_id):
    if not request.user.is_cliente:
        messages.error(request, 'Solo los clientes pueden cancelar sus citas.')
        return redirect('core:home')
    cita = get_object_or_404(Cita, id=cita_id, cliente=request.user.cliente)
    if request.method == 'POST':
        estado_cancelado = EstadoCita.objects.filter(tipo=EstadoCita.TIPO_CANCELADO).first()
        if cita.puede_cancelarse() and estado_cancelado:
            with transaction.atomic():
                cita.estado = estado_cancelado
                cita.save()

                transaction.on_commit(
                    lambda cita_id=cita.id: notificar_cita_cancelada(cita_id)
                )

            messages.success(request, f'Cita cancelada correctamente.')
        else:
            messages.error(request, 'Esta cita no puede cancelarse.')
        return redirect('citas:mis_citas')
    return redirect('citas:cita_detalle', cita_id=cita.id)


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
            fecha_base = timezone.localdate()
    else:
        fecha_base = timezone.localdate()

    filtro_mecanico = request.GET.get('mecanico', '')
    filtro_estado = request.GET.get('estado', '')

    def consultar(desde, hasta):
        citas = Cita.objects.filter(
            fecha__gte=desde, fecha__lte=hasta,
        ).select_related('cliente', 'motocicleta', 'mecanico', 'estado').order_by('fecha', 'hora')
        if filtro_mecanico:
            citas = citas.filter(mecanico__dui=filtro_mecanico)
        if filtro_estado:
            citas = citas.filter(estado=filtro_estado)
        return citas

    hoy = timezone.localdate()
    nombres_dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

    contexto = {
        'modo': modo,
        'fecha_base': fecha_base,
        'mecanicos': Mecanico.objects.filter(activo=True),
        'estados': EstadoCita.objects.all(),
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
    cambios = cita.cambios_estado.select_related('realizado_por', 'estado_anterior', 'estado_nuevo').all()

    # el flujo lo define el tipo de cada estado (ver EstadoCita.siguientes_posibles)
    estados_posibles = cita.estado.siguientes_posibles()
    puede_asignar_mecanico = not cita.estado.es_final

    # V2SCRUM-24: pasar a un estado de tipo completado exige registrar repuestos
    # usados y observaciones de cierre, así que esa transición se maneja con su
    # propio formulario ("finalizar_servicio") y se quita del selector genérico.
    estado_completado = estados_posibles.filter(tipo=EstadoCita.TIPO_COMPLETADO).first()
    puede_finalizar = estado_completado is not None
    opciones_estado_genericas = estados_posibles.exclude(tipo=EstadoCita.TIPO_COMPLETADO)
    productos_disponibles = Producto.objects.filter(activo=True).order_by('nombre')

    if request.method == 'POST':
        accion = request.POST.get('accion', '').strip()

        if accion == 'asignar_mecanico':
            if not puede_asignar_mecanico:
                messages.error(request, 'No se puede asignar mecánico a esta cita.')
                return redirect('citas:cita_admin_detalle', cita_id=cita.id)
            mecanico_dui = request.POST.get('mecanico_dui', '').strip()
            if not mecanico_dui:
                cita.mecanico = None
                cita.save(update_fields=['mecanico'])
                messages.success(request, 'Mecánico removido de la cita.')
                return redirect('citas:cita_admin_detalle', cita_id=cita.id)

            # El bloqueo evita que dos administradores asignen al mismo mecánico
            # en horarios cruzados al mismo tiempo.
            with transaction.atomic():
                mecanico = Mecanico.objects.select_for_update().filter(dui=mecanico_dui, activo=True).first()
                conflicto = cita_en_conflicto(mecanico, cita) if mecanico else None
                reasignada = cita.mecanico_id is not None
                if mecanico and not conflicto:
                    cita.mecanico = mecanico
                    cita.save(update_fields=['mecanico'])

            if not mecanico:
                messages.error(request, 'Mecánico no válido.')
            elif conflicto:
                messages.error(
                    request,
                    f'{mecanico.nombre} {mecanico.apellido} no está disponible: ya tiene la cita #{conflicto.id} '
                    f'a las {conflicto.hora.strftime("%H:%M")}, que se cruza con este horario.',
                )
            else:
                accion_hecha = 'Cita reasignada a' if reasignada else 'Mecánico asignado:'
                messages.success(request, f'{accion_hecha} {mecanico.nombre} {mecanico.apellido}.')
            return redirect('citas:cita_admin_detalle', cita_id=cita.id)

        elif accion == 'cambiar_estado':
            codigo_nuevo = request.POST.get('nuevo_estado', '').strip()
            motivo = request.POST.get('motivo', '').strip()

            # solo se acepta un estado permitido por el flujo desde el actual
            nuevo_estado = estados_posibles.filter(codigo=codigo_nuevo).first()
            if nuevo_estado is None:
                messages.error(request, 'Transición de estado no válida.')
                return redirect('citas:cita_admin_detalle', cita_id=cita.id)

            if nuevo_estado.tipo == EstadoCita.TIPO_COMPLETADO:
                messages.error(request, 'Para finalizar el servicio usá el formulario "Finalizar servicio".')
                return redirect('citas:cita_admin_detalle', cita_id=cita.id)

            if nuevo_estado.tipo == EstadoCita.TIPO_CANCELADO and not motivo:
                messages.error(request, 'El motivo es obligatorio para cancelar.')
                return redirect('citas:cita_admin_detalle', cita_id=cita.id)

            # el correo de confirmación se manda al salir del estado de Inicio hacia uno de Proceso
            es_confirmacion = (
                cita.estado.tipo == EstadoCita.TIPO_INICIO
                and nuevo_estado.tipo == EstadoCita.TIPO_PROCESO
            )

            with transaction.atomic():
                CambioEstadoCita.objects.create(
                    cita=cita,
                    estado_anterior=cita.estado,
                    estado_nuevo=nuevo_estado,
                    motivo=motivo,
                    realizado_por=request.user,
                )
                cita.estado = nuevo_estado
                cita.save(update_fields=['estado'])

                if es_confirmacion:
                    transaction.on_commit(
                        lambda cita_id=cita.id: notificar_cita_confirmada(cita_id)
                    )

            messages.success(request, f'Cita #{cita.id} actualizada a {nuevo_estado.nombre}.')
            return redirect('citas:calendario')

        elif accion == 'finalizar_servicio':
            """V2SCRUM-24: registra repuestos usados, observaciones de cierre,
            descuenta el inventario y pasa la cita a Completada."""
            if not puede_finalizar:
                messages.error(request, 'Esta cita no puede finalizarse desde su estado actual.')
                return redirect('citas:cita_admin_detalle', cita_id=cita.id)

            productos_ids = request.POST.getlist('producto_id')
            cantidades = request.POST.getlist('cantidad')
            observaciones_cierre = request.POST.get('observaciones_cierre', '').strip()

            repuestos_validados = []
            errores_repuestos = list(calcular_detalle_cita(cita)['errores'])
            productos_vistos = set()

            if len(productos_ids) != len(cantidades):
                errores_repuestos.append('Completá producto y cantidad en cada fila que agregues.')

            for producto_id, cantidad_str in zip(productos_ids, cantidades):
                producto_id = producto_id.strip()
                cantidad_str = cantidad_str.strip()
                if not producto_id and not cantidad_str:
                    continue  # fila vacía del formulario, se ignora

                if not producto_id or not cantidad_str:
                    errores_repuestos.append('Completá producto y cantidad en cada fila que agregues.')
                    continue

                try:
                    cantidad = int(cantidad_str)
                except ValueError:
                    errores_repuestos.append('La cantidad debe ser un número entero.')
                    continue

                if cantidad <= 0:
                    errores_repuestos.append('La cantidad debe ser mayor a cero.')
                    continue

                try:
                    producto = Producto.objects.get(id=producto_id, activo=True)
                except (Producto.DoesNotExist, ValueError):
                    errores_repuestos.append('Seleccionaste un producto inválido.')
                    continue

                if producto.id in productos_vistos:
                    errores_repuestos.append(f'"{producto.nombre}" está repetido en la lista.')
                    continue
                productos_vistos.add(producto.id)

                if not precio_valido(producto.precio):
                    errores_repuestos.append(f'El repuesto "{producto.nombre}" no tiene un precio válido.')
                    continue

                if cantidad > producto.stock_actual:
                    errores_repuestos.append(
                        f'No hay stock suficiente de "{producto.nombre}" '
                        f'(disponible: {producto.stock_actual}).'
                    )
                    continue

                repuestos_validados.append((producto, cantidad))

            if errores_repuestos:
                for error in errores_repuestos:
                    messages.error(request, error)
                return redirect('citas:cita_admin_detalle', cita_id=cita.id)

            with transaction.atomic():
                for producto, cantidad in repuestos_validados:
                    RepuestoUsado.objects.create(
                        cita=cita,
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=producto.precio,
                    )
                    producto.stock_actual = producto.stock_actual - cantidad
                    producto.save(update_fields=['stock_actual'])

                CambioEstadoCita.objects.create(
                    cita=cita,
                    estado_anterior=cita.estado,
                    estado_nuevo=estado_completado,
                    motivo=observaciones_cierre,
                    realizado_por=request.user,
                )
                cita.estado = estado_completado
                cita.observaciones_cierre = observaciones_cierre
                cita.save(update_fields=['estado', 'observaciones_cierre'])

                # V2SCRUM-33: correo de cierre con el ticket PDF adjunto
                # (V2SCRUM-30). Se dispara después de que la transacción de
                # finalización (repuestos, inventario, estado) se confirmó.
                transaction.on_commit(
                    lambda cita_id=cita.id: notificar_cita_completada(cita_id)
                )

            messages.success(
                request,
                f'Cita #{cita.id} finalizada. Inventario actualizado con {len(repuestos_validados)} repuesto(s).',
            )
            return redirect('citas:calendario')

        else:
            messages.error(request, 'Acción no reconocida.')
            return redirect('citas:cita_admin_detalle', cita_id=cita.id)

    return render(request, 'citas/cita_admin_detalle.html', {
        'cita': cita,
        'servicios': servicios,
        'cambios': cambios,
        'estados_posibles': estados_posibles,
        # Solo mecánicos libres en el horario de la cita (incluye al actual).
        'mecanicos': mecanicos_disponibles(cita) if puede_asignar_mecanico else [],
        'puede_asignar_mecanico': puede_asignar_mecanico,
        'opciones_estado': opciones_estado_genericas,
        'puede_finalizar': puede_finalizar,
        'productos_disponibles': productos_disponibles,
        'repuestos_usados': cita.repuestos_usados.select_related('producto').all(),
        'detalle_economico': calcular_detalle_cita(cita),
    })


@login_required(login_url='usuarios:login')
def mis_citas_mecanico(request):
    if not request.user.is_mecanico:
        messages.error(request, 'Solo los mecánicos pueden ver esta sección.')
        return redirect('core:home')

    dia_str = request.GET.get('dia', '').strip()
    estado_filtro = request.GET.get('estado', '').strip()

    citas = Cita.objects.select_related('cliente', 'motocicleta', 'estado').prefetch_related('servicios')

    dia = None
    if dia_str:
        try:
            dia = date.fromisoformat(dia_str)
        except ValueError:
            dia = None

    if dia:
        citas = citas.filter(fecha=dia)
    else:
        hoy = timezone.localdate()
        citas = citas.filter(fecha__gte=hoy, fecha__lte=hoy + timedelta(days=6))

    if estado_filtro:
        citas = citas.filter(estado=estado_filtro)

    citas = citas.order_by('fecha', 'hora')

    return render(request, 'citas/mis_citas_mecanico.html', {
        'citas': citas,
        'dia_str': dia_str,
        'estado_filtro': estado_filtro,
        'estados': EstadoCita.objects.all(),
    })


@login_required(login_url='usuarios:login')
def estados_cita(request):
    """Catálogo de estados de cita: listar, crear, editar y activar/desactivar."""
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    # de estos tipos el sistema necesita exactamente uno (agendar, finalizar y cancelar dependen de ellos)
    TIPOS_UNICOS = [EstadoCita.TIPO_INICIO, EstadoCita.TIPO_COMPLETADO, EstadoCita.TIPO_CANCELADO]

    estados = EstadoCita.objects.all()

    estado_editar = None
    editar_codigo = request.GET.get('editar')
    if editar_codigo:
        estado_editar = get_object_or_404(EstadoCita, codigo=editar_codigo)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'guardar':
            errores = {}
            codigo_editar = request.POST.get('codigo', '').strip()
            if codigo_editar:
                estado_editar = get_object_or_404(EstadoCita, codigo=codigo_editar)

            datos = {
                'nombre': request.POST.get('nombre', '').strip(),
                'tipo':   request.POST.get('tipo', '').strip(),
            }

            if not datos['nombre']:
                errores['nombre'] = 'El nombre es obligatorio.'
            elif len(datos['nombre']) > 50:
                errores['nombre'] = 'El nombre no puede pasar de 50 caracteres.'
            else:
                repetido = EstadoCita.objects.filter(nombre__iexact=datos['nombre'])
                if estado_editar:
                    repetido = repetido.exclude(codigo=estado_editar.codigo)
                if repetido.exists():
                    errores['nombre'] = 'Ya existe un estado con ese nombre.'

            if datos['tipo'] not in dict(EstadoCita.TIPOS):
                errores['tipo'] = 'Elegí un tipo válido.'
            elif estado_editar and estado_editar.tipo in TIPOS_UNICOS and datos['tipo'] != estado_editar.tipo:
                errores['tipo'] = 'El tipo de este estado no se puede cambiar: el sistema necesita uno de este tipo.'
            elif datos['tipo'] in TIPOS_UNICOS:
                existente = EstadoCita.objects.filter(tipo=datos['tipo'])
                if estado_editar:
                    existente = existente.exclude(codigo=estado_editar.codigo)
                if existente.exists():
                    errores['tipo'] = (
                        f'Ya existe un estado de tipo "{dict(EstadoCita.TIPOS)[datos["tipo"]]}" '
                        f'({existente.first().nombre}). Solo puede haber uno.'
                    )

            if errores:
                return render(request, 'citas/estados_cita.html', {
                    'estados': estados,
                    'tipos': EstadoCita.TIPOS,
                    'tipos_unicos': TIPOS_UNICOS,
                    'errores': errores,
                    'datos': datos,
                    'estado_editar': estado_editar,
                    'mostrar_form': True,
                })

            if estado_editar:
                estado_editar.nombre = datos['nombre']
                estado_editar.tipo = datos['tipo']
                estado_editar.save(update_fields=['nombre', 'tipo'])
                messages.success(request, f'Estado "{estado_editar.nombre}" actualizado.')
            else:
                # el código se genera del nombre y no cambia nunca (es la PK)
                base = slugify(datos['nombre']).replace('-', '_')[:25] or 'estado'
                codigo = base
                numero = 2
                while EstadoCita.objects.filter(codigo=codigo).exists():
                    codigo = f'{base}_{numero}'
                    numero += 1

                # el nuevo estado va al final de la lista y toma el color de su tipo
                ultimo = EstadoCita.objects.order_by('-orden').first()
                EstadoCita.objects.create(
                    codigo=codigo,
                    nombre=datos['nombre'],
                    tipo=datos['tipo'],
                    color=EstadoCita.COLORES[datos['tipo']],
                    orden=ultimo.orden + 1 if ultimo else 1,
                )
                messages.success(request, f'Estado "{datos["nombre"]}" creado.')

            return redirect('citas:estados_cita')

        elif accion == 'desactivar':
            estado = get_object_or_404(EstadoCita, codigo=request.POST.get('codigo'))
            if estado.tipo in TIPOS_UNICOS:
                messages.error(request, f'"{estado.nombre}" no se puede desactivar: el sistema necesita un estado de tipo {estado.get_tipo_display()}.')
                return redirect('citas:estados_cita')
            citas_en_estado = estado.citas.count()
            if citas_en_estado:
                messages.error(request, f'"{estado.nombre}" no se puede desactivar: tiene {citas_en_estado} cita(s) en ese estado.')
                return redirect('citas:estados_cita')
            estado.activo = False
            estado.save(update_fields=['activo'])
            messages.success(request, f'Estado "{estado.nombre}" desactivado.')
            return redirect('citas:estados_cita')

        elif accion == 'activar':
            estado = get_object_or_404(EstadoCita, codigo=request.POST.get('codigo'))
            estado.activo = True
            estado.save(update_fields=['activo'])
            messages.success(request, f'Estado "{estado.nombre}" activado.')
            return redirect('citas:estados_cita')

    return render(request, 'citas/estados_cita.html', {
        'estados': estados,
        'tipos': EstadoCita.TIPOS,
        'tipos_unicos': TIPOS_UNICOS,
        'errores': {},
        'datos': {},
        'estado_editar': estado_editar,
        'mostrar_form': bool(request.GET.get('mostrar_form') or estado_editar),
    })


@login_required(login_url='usuarios:login')
def reporte_servicios(request):
    """V2SCRUM-39. Reporte de servicios del taller por período, con filtros
    de servicio/mecánico y export a PDF o Excel.
    """
    if not request.user.is_admin:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
        return redirect('core:home')

    desde, hasta = rango_fechas(request)
    servicio_id = request.GET.get('servicio') or None
    mecanico_dui = request.GET.get('mecanico') or None

    datos = calcular_reporte_servicios(desde, hasta, servicio_id, mecanico_dui)

    exportar = request.GET.get('export')
    if exportar == 'pdf':
        pdf_bytes = generar_reporte_pdf(desde, hasta, datos)
        respuesta = HttpResponse(pdf_bytes, content_type='application/pdf')
        respuesta['Content-Disposition'] = f'attachment; filename="reporte_servicios_{desde}_{hasta}.pdf"'
        return respuesta

    if exportar == 'xlsx':
        xlsx_bytes = generar_reporte_excel(desde, hasta, datos)
        respuesta = HttpResponse(
            xlsx_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        respuesta['Content-Disposition'] = f'attachment; filename="reporte_servicios_{desde}_{hasta}.xlsx"'
        return respuesta

    return render(request, 'citas/reporte_servicios.html', {
        'desde': desde,
        'hasta': hasta,
        'servicio_id': servicio_id,
        'mecanico_dui': mecanico_dui,
        'servicios': Servicio.objects.filter(activo=True).order_by('nombre'),
        'mecanicos': Mecanico.objects.order_by('apellido', 'nombre'),
        **datos,
    })
