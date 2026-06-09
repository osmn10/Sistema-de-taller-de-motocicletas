"""Resetea la BD y la puebla con datos de demo. Borra TODO y vuelve a crear."""

from datetime import time, timedelta, date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.citas.models import CambioEstadoCita, Cita, ServicioCita
from apps.configuracion.models import HorarioTaller
from apps.productos.models import Producto, Proveedor
from apps.servicios.models import Servicio
from apps.usuarios.models import Cliente, Mecanico, Usuario
from apps.vehiculos.models import Motocicleta


class Command(BaseCommand):
    help = 'Borra todos los datos y carga datos de demo (admin, 2 mecánicos, 2 proveedores, clientes, motos, servicios, productos, citas).'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Limpiando datos existentes…'))
        self._limpiar()

        self.stdout.write(self.style.NOTICE('Sembrando datos de demo…'))
        self._seed_admin()
        mecanicos = self._seed_mecanicos()
        self._seed_horario()
        servicios = self._seed_servicios()
        self._seed_proveedores_y_productos()
        clientes = self._seed_clientes_y_motos()
        self._seed_citas(clientes, servicios)

        self.stdout.write(self.style.SUCCESS('Listo. Datos de demo cargados.'))

    def _limpiar(self):
        CambioEstadoCita.objects.all().delete()
        ServicioCita.objects.all().delete()
        Cita.objects.all().delete()
        Motocicleta.objects.all().delete()
        Producto.objects.all().delete()
        Proveedor.objects.all().delete()
        Servicio.objects.all().delete()
        HorarioTaller.objects.all().delete()
        Usuario.objects.all().delete()  # borra clientes, mecánicos y admin (herencia)

    def _seed_admin(self):
        Usuario.objects.create_superuser(
            dui='00000000-0',
            nombre='Admin',
            apellido='Taller',
            telefono='0000-0000',
            email='admin@taller.com',
            password='admin12345',
        )
        self.stdout.write('  · admin creado (00000000-0 / admin12345)')

    def _seed_mecanicos(self):
        datos = [
            {'dui': '55555555-5', 'nombre': 'Juan', 'apellido': 'Martínez',
             'telefono': '7777-1111', 'email': 'juan@taller.com',
             'especialidad': Mecanico.ESPECIALIDAD_MECANICA_GENERAL},
            {'dui': '66666666-6', 'nombre': 'Roberto', 'apellido': 'Sánchez',
             'telefono': '7777-2222', 'email': 'roberto@taller.com',
             'especialidad': Mecanico.ESPECIALIDAD_MOTOR},
        ]
        mecanicos = []
        for d in datos:
            m = Mecanico(
                dui=d['dui'], nombre=d['nombre'], apellido=d['apellido'],
                telefono=d['telefono'], email=d['email'], especialidad=d['especialidad'],
            )
            m.set_password('mecanico123')
            m.save()
            mecanicos.append(m)
            self.stdout.write(f"  · mecánico {d['nombre']} {d['apellido']} ({d['dui']})")
        return mecanicos

    def _seed_horario(self):
        horario = [
            (HorarioTaller.LUNES,     True,  time(8, 0), time(17, 0)),
            (HorarioTaller.MARTES,    True,  time(8, 0), time(17, 0)),
            (HorarioTaller.MIERCOLES, True,  time(8, 0), time(17, 0)),
            (HorarioTaller.JUEVES,    True,  time(8, 0), time(17, 0)),
            (HorarioTaller.VIERNES,   True,  time(8, 0), time(17, 0)),
            (HorarioTaller.SABADO,    True,  time(9, 0), time(13, 0)),
            (HorarioTaller.DOMINGO,   False, None,       None),
        ]
        for dia, abierto, apertura, cierre in horario:
            HorarioTaller.objects.create(
                dia_semana=dia, abierto=abierto,
                hora_apertura=apertura, hora_cierre=cierre,
            )

    def _seed_servicios(self):
        datos = [
            {'nombre': 'Cambio de aceite', 'descripcion': 'Drenado y cambio de aceite del motor con filtro nuevo.', 'precio_base': 15.00, 'duracion_estimada': 30},
            {'nombre': 'Afinamiento general', 'descripcion': 'Limpieza y ajuste del sistema de combustión y carburador.', 'precio_base': 35.00, 'duracion_estimada': 60},
            {'nombre': 'Cambio de pastillas de freno', 'descripcion': 'Sustitución de pastillas delanteras y traseras.', 'precio_base': 25.00, 'duracion_estimada': 60},
            {'nombre': 'Revisión eléctrica', 'descripcion': 'Diagnóstico del sistema eléctrico y batería.', 'precio_base': 20.00, 'duracion_estimada': 60},
            {'nombre': 'Ajuste y lubricación de cadena', 'descripcion': 'Tensado y engrase de la cadena de transmisión.', 'precio_base': 10.00, 'duracion_estimada': 30},
            {'nombre': 'Cambio de llantas', 'descripcion': 'Montaje de llantas nuevas (no incluye el repuesto).', 'precio_base': 30.00, 'duracion_estimada': 60},
        ]
        servicios = {}
        for s in datos:
            servicios[s['nombre']] = Servicio.objects.create(**s)
        return servicios

    def _seed_proveedores_y_productos(self):
        prov1 = Proveedor.objects.create(
            nit='0614-150385-101-2', nombre='Repuestos del Oriente S.A. de C.V.',
            telefono='2660-1234', email='ventas@repuestosoriente.com',
        )
        prov2 = Proveedor.objects.create(
            nit='0210-220490-102-5', nombre='MotoPartes El Salvador',
            telefono='2225-6789', email='contacto@motopartessv.com',
        )
        self.stdout.write('  · 2 proveedores creados')
        productos = [
            ('Aceite 10W-40 (1L)',           6.50,  40, 10, prov1),
            ('Filtro de aceite universal',   4.00,  25, 8,  prov1),
            ('Pastillas de freno delantera', 12.00, 15, 5,  prov2),
            ('Cadena 428H x 120 eslabones',  22.00, 8,  4,  prov2),
            ('Bujía NGK estándar',           3.50,  50, 15, prov1),
            ('Llanta 90/90-17 trasera',      35.00, 6,  3,  prov2),
        ]
        for nombre, precio, stock, minimo, prov in productos:
            Producto.objects.create(
                nombre=nombre, precio=precio, stock_actual=stock,
                stock_minimo=minimo, proveedor=prov,
            )

    def _seed_clientes_y_motos(self):
        datos = [
            {'dui': '11111111-1', 'nombre': 'Pedro', 'apellido': 'Pérez',
             'telefono': '7000-1111', 'email': 'pedro@correo.com',
             'direccion': 'Col. Las Flores #45, San Miguel',
             'motos': [
                 ('M-1234', 'Honda', 'CG 150', 2020, 'Rojo', 12500),
                 ('M-5678', 'Yamaha', 'YBR 125', 2019, 'Negro', 25300),
             ]},
            {'dui': '22222222-2', 'nombre': 'María', 'apellido': 'López',
             'telefono': '7000-2222', 'email': 'maria@correo.com',
             'direccion': 'Barrio El Centro, calle 3 #12',
             'motos': [('M-2222', 'Suzuki', 'GN 125', 2021, 'Azul', 8200)]},
            {'dui': '33333333-3', 'nombre': 'Carlos', 'apellido': 'Ruiz',
             'telefono': '7000-3333', 'email': 'carlos@correo.com',
             'direccion': 'Col. Las Mercedes #88',
             'motos': [('M-3333', 'Honda', 'XR 150L', 2022, 'Blanco', 5400)]},
        ]
        clientes = {}
        for c in datos:
            cliente = Cliente(
                dui=c['dui'], nombre=c['nombre'], apellido=c['apellido'],
                telefono=c['telefono'], email=c['email'], direccion=c['direccion'],
            )
            cliente.set_password('cliente123')
            cliente.save()
            for placa, marca, modelo, anio, color, km in c['motos']:
                Motocicleta.objects.create(
                    placa=placa, cliente=cliente, marca=marca, modelo=modelo,
                    anio=anio, color=color, kilometraje=km,
                )
            clientes[c['dui']] = cliente
            self.stdout.write(f"  · cliente {c['nombre']} {c['apellido']} ({c['dui']})")
        return clientes

    def _seed_citas(self, clientes, servicios):
        hoy = date.today()
        # (dui_cliente, placa, dias_desde_hoy, hora, estado, [nombres_servicios])
        plan = [
            ('11111111-1', 'M-1234', 3,   time(9, 0),  Cita.ESTADO_PENDIENTE,  ['Cambio de aceite']),
            ('11111111-1', 'M-1234', 5,   time(10, 0), Cita.ESTADO_CONFIRMADA, ['Afinamiento general', 'Ajuste y lubricación de cadena']),
            ('11111111-1', 'M-5678', -10, time(8, 30), Cita.ESTADO_COMPLETADA, ['Cambio de aceite', 'Revisión eléctrica']),
            ('11111111-1', 'M-1234', 2,   time(11, 0), Cita.ESTADO_CANCELADA,  ['Cambio de pastillas de freno']),
            ('22222222-2', 'M-2222', 4,   time(9, 0),  Cita.ESTADO_PENDIENTE,  ['Afinamiento general']),
            ('33333333-3', 'M-3333', -5,  time(14, 0), Cita.ESTADO_COMPLETADA, ['Cambio de llantas']),
        ]
        for dui, placa, delta, hora, estado, nombres in plan:
            cliente = clientes[dui]
            moto = Motocicleta.objects.get(placa=placa)
            cita = Cita.objects.create(
                cliente=cliente, motocicleta=moto, mecanico=None,
                fecha=hoy + timedelta(days=delta), hora=hora, estado=estado,
            )
            for nombre in nombres:
                servicio = servicios[nombre]
                ServicioCita.objects.create(
                    cita=cita, servicio=servicio, precio_final=servicio.precio_base,
                )
        self.stdout.write(f'  · {len(plan)} citas de demo creadas')
