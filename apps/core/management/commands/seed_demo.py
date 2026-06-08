"""Pobla la BD con datos de demo. Idempotente: usar las veces que quieras."""

from datetime import time

from django.core.management.base import BaseCommand

from apps.configuracion.models import HorarioTaller
from apps.productos.models import Producto, Proveedor
from apps.servicios.models import Servicio
from apps.usuarios.models import Cliente, Mecanico, Usuario
from apps.vehiculos.models import Motocicleta


class Command(BaseCommand):
    help = 'Pobla la BD con datos de demo (admin, clientes, motos, mecánicos, servicios, horario, productos).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Sembrando datos de demo…'))

        self._seed_admin()
        self._seed_mecanicos()
        self._seed_clientes_y_motos()
        self._seed_servicios()
        self._seed_horario()
        self._seed_proveedores_y_productos()

        self.stdout.write(self.style.SUCCESS('Listo. Datos de demo cargados.'))

    def _seed_admin(self):
        if Usuario.objects.filter(dui='00000000-0').exists():
            self.stdout.write('  · admin ya existía')
            return
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
        mecanicos = [
            {
                'dui': '55555555-5',
                'nombre': 'Juan', 'apellido': 'Martínez',
                'telefono': '7777-1111', 'email': 'juan@taller.com',
                'especialidad': Mecanico.ESPECIALIDAD_MECANICA_GENERAL,
            },
            {
                'dui': '66666666-6',
                'nombre': 'Roberto', 'apellido': 'Sánchez',
                'telefono': '7777-2222', 'email': 'roberto@taller.com',
                'especialidad': Mecanico.ESPECIALIDAD_MOTOR,
            },
            {
                'dui': '77777777-7',
                'nombre': 'Diego', 'apellido': 'Ramírez',
                'telefono': '7777-3333', 'email': 'diego@taller.com',
                'especialidad': Mecanico.ESPECIALIDAD_ELECTRICO,
            },
        ]
        for data in mecanicos:
            if Usuario.objects.filter(dui=data['dui']).exists():
                continue
            m = Mecanico(
                dui=data['dui'],
                nombre=data['nombre'],
                apellido=data['apellido'],
                telefono=data['telefono'],
                email=data['email'],
                especialidad=data['especialidad'],
            )
            m.set_password('mecanico123')
            m.save()
            self.stdout.write(f"  · mecánico {data['nombre']} {data['apellido']} ({data['dui']})")

    def _seed_clientes_y_motos(self):
        clientes = [
            {
                'dui': '11111111-1', 'nombre': 'Pedro', 'apellido': 'Pérez',
                'telefono': '7000-1111', 'email': 'pedro@correo.com',
                'direccion': 'Col. Las Flores #45, San Miguel',
                'motos': [
                    {'placa': 'M-1234', 'marca': 'Honda', 'modelo': 'CG 150', 'anio': 2020, 'color': 'Rojo', 'kilometraje': 12500},
                    {'placa': 'M-5678', 'marca': 'Yamaha', 'modelo': 'YBR 125', 'anio': 2019, 'color': 'Negro', 'kilometraje': 25300},
                ],
            },
            {
                'dui': '22222222-2', 'nombre': 'María', 'apellido': 'López',
                'telefono': '7000-2222', 'email': 'maria@correo.com',
                'direccion': 'Barrio El Centro, calle 3 #12',
                'motos': [
                    {'placa': 'M-2222', 'marca': 'Suzuki', 'modelo': 'GN 125', 'anio': 2021, 'color': 'Azul', 'kilometraje': 8200},
                ],
            },
            {
                'dui': '33333333-3', 'nombre': 'Carlos', 'apellido': 'Ruiz',
                'telefono': '7000-3333', 'email': 'carlos@correo.com',
                'direccion': 'Col. Las Mercedes #88',
                'motos': [
                    {'placa': 'M-3333', 'marca': 'Honda', 'modelo': 'XR 150L', 'anio': 2022, 'color': 'Blanco', 'kilometraje': 5400},
                ],
            },
            {
                'dui': '44444444-4', 'nombre': 'Ana', 'apellido': 'García',
                'telefono': '7000-4444', 'email': 'ana@correo.com',
                'direccion': 'Col. Ciudad Jardín pasaje 5 #2',
                'motos': [
                    {'placa': 'M-4444', 'marca': 'Bajaj', 'modelo': 'Pulsar NS 200', 'anio': 2023, 'color': 'Rojo', 'kilometraje': 1100},
                ],
            },
        ]
        for c in clientes:
            if not Usuario.objects.filter(dui=c['dui']).exists():
                cliente = Cliente(
                    dui=c['dui'], nombre=c['nombre'], apellido=c['apellido'],
                    telefono=c['telefono'], email=c['email'], direccion=c['direccion'],
                )
                cliente.set_password('cliente123')
                cliente.save()
                self.stdout.write(f"  · cliente {c['nombre']} {c['apellido']} ({c['dui']})")
            cliente = Cliente.objects.get(dui=c['dui'])
            for m in c['motos']:
                Motocicleta.objects.get_or_create(
                    placa=m['placa'],
                    defaults={
                        'cliente': cliente,
                        'marca': m['marca'], 'modelo': m['modelo'],
                        'anio': m['anio'], 'color': m['color'],
                        'kilometraje': m['kilometraje'],
                    },
                )

    def _seed_servicios(self):
        servicios = [
            {'nombre': 'Cambio de aceite', 'descripcion': 'Drenado y cambio de aceite del motor con filtro nuevo.', 'precio_base': 15.00, 'duracion_estimada': 30},
            {'nombre': 'Afinamiento general', 'descripcion': 'Limpieza y ajuste del sistema de combustión y carburador.', 'precio_base': 35.00, 'duracion_estimada': 60},
            {'nombre': 'Cambio de pastillas de freno', 'descripcion': 'Sustitución de pastillas delanteras y traseras.', 'precio_base': 25.00, 'duracion_estimada': 60},
            {'nombre': 'Revisión eléctrica', 'descripcion': 'Diagnóstico del sistema eléctrico y batería.', 'precio_base': 20.00, 'duracion_estimada': 60},
            {'nombre': 'Ajuste y lubricación de cadena', 'descripcion': 'Tensado y engrase de la cadena de transmisión.', 'precio_base': 10.00, 'duracion_estimada': 30},
            {'nombre': 'Cambio de llantas', 'descripcion': 'Montaje de llantas nuevas (no incluye el repuesto).', 'precio_base': 30.00, 'duracion_estimada': 60},
        ]
        for s in servicios:
            Servicio.objects.get_or_create(nombre=s['nombre'], defaults=s)

    def _seed_horario(self):
        horario = [
            (HorarioTaller.LUNES,     True,  time(8, 0), time(17, 0)),
            (HorarioTaller.MARTES,    True,  time(8, 0), time(17, 0)),
            (HorarioTaller.MIERCOLES, True,  time(8, 0), time(17, 0)),
            (HorarioTaller.JUEVES,    True,  time(8, 0), time(17, 0)),
            (HorarioTaller.VIERNES,   True,  time(8, 0), time(17, 0)),
            (HorarioTaller.SABADO,    True,  time(9, 0), time(13, 0)),
            (HorarioTaller.DOMINGO,   False, None,        None),
        ]
        for dia, abierto, apertura, cierre in horario:
            HorarioTaller.objects.update_or_create(
                dia_semana=dia,
                defaults={'abierto': abierto, 'hora_apertura': apertura, 'hora_cierre': cierre},
            )

    def _seed_proveedores_y_productos(self):
        proveedor, _ = Proveedor.objects.get_or_create(
            nit='0614-150385-101-2',
            defaults={'nombre': 'Repuestos del Oriente S.A. de C.V.', 'telefono': '2660-1234', 'email': 'ventas@repuestosoriente.com'},
        )
        productos = [
            {'nombre': 'Aceite 10W-40 (1L)',          'precio': 6.50,  'stock_actual': 40, 'stock_minimo': 10},
            {'nombre': 'Filtro de aceite universal',  'precio': 4.00,  'stock_actual': 25, 'stock_minimo': 8},
            {'nombre': 'Pastillas de freno delantera','precio': 12.00, 'stock_actual': 15, 'stock_minimo': 5},
            {'nombre': 'Cadena 428H x 120 eslabones', 'precio': 22.00, 'stock_actual': 8,  'stock_minimo': 4},
            {'nombre': 'Bujía NGK estándar',          'precio': 3.50,  'stock_actual': 50, 'stock_minimo': 15},
            {'nombre': 'Llanta 90/90-17 trasera',     'precio': 35.00, 'stock_actual': 6,  'stock_minimo': 3},
        ]
        for p in productos:
            Producto.objects.get_or_create(
                nombre=p['nombre'],
                defaults={**p, 'proveedor': proveedor},
            )
