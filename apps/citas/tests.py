from datetime import date, time, timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.productos.models import Producto
from apps.servicios.models import Servicio
from apps.usuarios.models import Mecanico, Usuario
from apps.vehiculos.models import Motocicleta

from .models import Cita, RepuestoUsado, ServicioCita
from .services import (
    notificar_cita_agendada,
    notificar_cita_cancelada,
    notificar_cita_confirmada,
    notificar_cita_reagendada,
)
from .totales import calcular_detalle_cita
from .ticket_pdf import generar_ticket_pdf


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    TALLER_NOMBRE='Taller de prueba',
    TALLER_DIRECCION='San Miguel, El Salvador',
)
class NotificacionesCitaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cliente = Usuario.objects.create_cliente(
            dui='11111111-1',
            password='cliente123',
            nombre='Ana',
            apellido='López',
            telefono='7000-1111',
            email='ana@example.com',
            direccion='San Miguel',
        )
        cls.admin = Usuario.objects.create_admin(
            dui='22222222-2',
            password='admin123',
            nombre='Alex',
            apellido='Admin',
            telefono='7000-2222',
            email='admin@example.com',
        )
        Usuario.objects.create_mecanico(
            dui='33333333-3',
            password='mecanico123',
            nombre='Mario',
            apellido='Mecánico',
            telefono='7000-3333',
            email='mario@example.com',
            especialidad=Mecanico.ESPECIALIDAD_MECANICA_GENERAL,
        )
        cls.motocicleta = Motocicleta.objects.create(
            placa='M-1234',
            cliente=cls.cliente,
            marca='Honda',
            modelo='CG 150',
            anio=2024,
            color='Negro',
        )
        cls.servicio = Servicio.objects.create(
            nombre='Cambio de aceite',
            precio_base='15.00',
            duracion_estimada=30,
        )

    def crear_cita(self, estado=Cita.ESTADO_PENDIENTE):
        cita = Cita.objects.create(
            cliente=self.cliente,
            motocicleta=self.motocicleta,
            fecha=date.today() + timedelta(days=2),
            hora=time(9, 0),
            estado=estado,
        )
        ServicioCita.objects.create(
            cita=cita,
            servicio=self.servicio,
            precio_final=self.servicio.precio_base,
        )
        return cita

    def test_correo_de_cita_agendada_incluye_detalles(self):
        cita = self.crear_cita()

        enviado = notificar_cita_agendada(cita.id)

        self.assertTrue(enviado)
        self.assertEqual(len(mail.outbox), 1)
        mensaje = mail.outbox[0]
        self.assertEqual(mensaje.to, ['ana@example.com'])
        self.assertIn(f'Cita #{cita.id} agendada', mensaje.subject)
        contenido_html, tipo_mime = mensaje.alternatives[0]
        self.assertEqual(tipo_mime, 'text/html')
        self.assertIn('Cambio de aceite', contenido_html)
        self.assertIn('M-1234', contenido_html)

    def test_correo_de_cita_confirmada_incluye_direccion(self):
        cita = self.crear_cita(estado=Cita.ESTADO_CONFIRMADA)

        enviado = notificar_cita_confirmada(cita.id)

        self.assertTrue(enviado)
        mensaje = mail.outbox[0]
        self.assertIn(f'Cita #{cita.id} confirmada', mensaje.subject)
        contenido_html, _ = mensaje.alternatives[0]
        self.assertIn('San Miguel, El Salvador', contenido_html)

    @patch('apps.citas.views.notificar_cita_agendada')
    def test_agendar_dispara_notificacion_despues_de_guardar(self, notificar):
        self.client.force_login(self.cliente)
        fecha = date.today() + timedelta(days=3)
        url = reverse('citas:agendar_cita')
        url = f'{url}?fecha={fecha.isoformat()}&hora=09:00&servicio={self.servicio.id}'

        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(
                url,
                {
                    'motocicleta': self.motocicleta.placa,
                    'observaciones': 'Prueba automática',
                },
            )

        self.assertEqual(respuesta.status_code, 302)
        cita = Cita.objects.get(fecha=fecha)
        notificar.assert_called_once_with(cita.id)

    @patch('apps.citas.views.notificar_cita_confirmada')
    def test_confirmar_dispara_segunda_notificacion(self, notificar):
        cita = self.crear_cita()
        self.client.force_login(self.admin)

        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(
                reverse('citas:cita_admin_detalle', args=[cita.id]),
                {
                    'accion': 'cambiar_estado',
                    'nuevo_estado': Cita.ESTADO_CONFIRMADA,
                    'motivo': '',
                },
            )

        self.assertEqual(respuesta.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.ESTADO_CONFIRMADA)
        notificar.assert_called_once_with(cita.id)

    def test_correo_de_cita_cancelada_incluye_detalles(self):
        cita = self.crear_cita()

        enviado = notificar_cita_cancelada(cita.id)

        self.assertTrue(enviado)
        self.assertEqual(len(mail.outbox), 1)
        mensaje = mail.outbox[0]
        self.assertEqual(mensaje.to, ['ana@example.com'])
        self.assertIn(f'Cita #{cita.id} cancelada', mensaje.subject)
        contenido_html, tipo_mime = mensaje.alternatives[0]
        self.assertEqual(tipo_mime, 'text/html')
        self.assertIn('Cambio de aceite', contenido_html)
        self.assertIn('M-1234', contenido_html)

    def test_correo_de_cita_reagendada_incluye_fecha_anterior(self):
        cita = self.crear_cita(estado=Cita.ESTADO_CONFIRMADA)
        fecha_anterior = cita.fecha
        hora_anterior = cita.hora
        cita.fecha = cita.fecha + timedelta(days=5)
        cita.hora = time(11, 0)
        cita.save()

        enviado = notificar_cita_reagendada(cita.id, fecha_anterior, hora_anterior)

        self.assertTrue(enviado)
        mensaje = mail.outbox[0]
        self.assertIn(f'Cita #{cita.id} reagendada', mensaje.subject)
        contenido_html, _ = mensaje.alternatives[0]
        self.assertIn(fecha_anterior.strftime('%d/%m/%Y'), contenido_html)
        self.assertIn(cita.fecha.strftime('%d/%m/%Y'), contenido_html)

    @patch('apps.citas.views.notificar_cita_cancelada')
    def test_cancelar_dispara_notificacion_despues_de_guardar(self, notificar):
        cita = self.crear_cita()
        self.client.force_login(self.cliente)

        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(
                reverse('citas:cancelar_cita', args=[cita.id]),
            )

        self.assertEqual(respuesta.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.ESTADO_CANCELADA)
        notificar.assert_called_once_with(cita.id)

    @patch('apps.citas.views.notificar_cita_reagendada')
    def test_reagendar_dispara_notificacion_despues_de_guardar(self, notificar):
        cita = self.crear_cita()
        fecha_anterior = cita.fecha
        hora_anterior = cita.hora
        nueva_fecha = fecha_anterior + timedelta(days=3)
        self.client.force_login(self.cliente)

        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(
                reverse('citas:reagendar_cita', args=[cita.id]),
                {'fecha': nueva_fecha.isoformat(), 'hora': '10:00'},
            )

        self.assertEqual(respuesta.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.fecha, nueva_fecha)
        notificar.assert_called_once_with(cita.id, fecha_anterior, hora_anterior)


class FinalizarServicioTests(TestCase):
    """V2SCRUM-24: registrar repuestos usados y finalizar la cita."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = Usuario.objects.create_cliente(
            dui='44444444-4',
            password='cliente123',
            nombre='Carlos',
            apellido='Pérez',
            telefono='7000-4444',
            email='carlos@example.com',
            direccion='San Salvador',
        )
        cls.admin = Usuario.objects.create_admin(
            dui='55555555-5',
            password='admin123',
            nombre='Alex',
            apellido='Admin',
            telefono='7000-5555',
            email='admin2@example.com',
        )
        cls.mecanico = Usuario.objects.create_mecanico(
            dui='66666666-6',
            password='mecanico123',
            nombre='Mario',
            apellido='Mecánico',
            telefono='7000-6666',
            email='mario2@example.com',
            especialidad=Mecanico.ESPECIALIDAD_MECANICA_GENERAL,
        )
        cls.motocicleta = Motocicleta.objects.create(
            placa='M-9999',
            cliente=cls.cliente,
            marca='Yamaha',
            modelo='FZ 150',
            anio=2023,
            color='Azul',
        )
        cls.servicio = Servicio.objects.create(
            nombre='Ajuste de motor',
            precio_base='40.00',
            duracion_estimada=60,
        )

    def setUp(self):
        self.producto = Producto.objects.create(
            nombre='Pastilla de freno',
            precio='12.50',
            stock_actual=10,
            stock_minimo=2,
        )

    def crear_cita_en_proceso(self):
        cita = Cita.objects.create(
            cliente=self.cliente,
            motocicleta=self.motocicleta,
            mecanico=self.mecanico,
            fecha=date.today(),
            hora=time(9, 0),
            estado=Cita.ESTADO_EN_PROCESO,
        )
        ServicioCita.objects.create(
            cita=cita,
            servicio=self.servicio,
            precio_final=self.servicio.precio_base,
        )
        return cita

    def test_finalizar_descuenta_inventario_y_completa_la_cita(self):
        cita = self.crear_cita_en_proceso()
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse('citas:cita_admin_detalle', args=[cita.id]),
            {
                'accion': 'finalizar_servicio',
                'producto_id': [str(self.producto.id)],
                'cantidad': ['3'],
                'observaciones_cierre': 'Se cambió pastilla de freno trasera.',
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        cita.refresh_from_db()
        self.producto.refresh_from_db()

        self.assertEqual(cita.estado, Cita.ESTADO_COMPLETADA)
        self.assertEqual(cita.observaciones_cierre, 'Se cambió pastilla de freno trasera.')
        self.assertEqual(self.producto.stock_actual, 7)
        self.assertEqual(RepuestoUsado.objects.filter(cita=cita).count(), 1)
        repuesto = RepuestoUsado.objects.get(cita=cita)
        self.assertEqual(repuesto.producto, self.producto)
        self.assertEqual(repuesto.cantidad, 3)

        cambio = cita.cambios_estado.first()
        self.assertEqual(cambio.estado_nuevo, Cita.ESTADO_COMPLETADA)
        self.assertEqual(cambio.estado_anterior, Cita.ESTADO_EN_PROCESO)

    def test_finalizar_sin_repuestos_es_valido(self):
        cita = self.crear_cita_en_proceso()
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse('citas:cita_admin_detalle', args=[cita.id]),
            {
                'accion': 'finalizar_servicio',
                'producto_id': [''],
                'cantidad': [''],
                'observaciones_cierre': 'Servicio de rutina, sin repuestos.',
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.ESTADO_COMPLETADA)
        self.assertEqual(RepuestoUsado.objects.filter(cita=cita).count(), 0)

    def test_finalizar_rechaza_stock_insuficiente(self):
        cita = self.crear_cita_en_proceso()
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse('citas:cita_admin_detalle', args=[cita.id]),
            {
                'accion': 'finalizar_servicio',
                'producto_id': [str(self.producto.id)],
                'cantidad': ['999'],
                'observaciones_cierre': '',
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        cita.refresh_from_db()
        self.producto.refresh_from_db()

        self.assertEqual(cita.estado, Cita.ESTADO_EN_PROCESO)
        self.assertEqual(self.producto.stock_actual, 10)
        self.assertEqual(RepuestoUsado.objects.filter(cita=cita).count(), 0)

    def test_finalizar_requiere_que_la_cita_este_en_proceso(self):
        cita = self.crear_cita_en_proceso()
        cita.estado = Cita.ESTADO_PENDIENTE
        cita.save(update_fields=['estado'])
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse('citas:cita_admin_detalle', args=[cita.id]),
            {
                'accion': 'finalizar_servicio',
                'producto_id': [''],
                'cantidad': [''],
                'observaciones_cierre': '',
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.ESTADO_PENDIENTE)

    def test_cambiar_estado_generico_no_permite_completar_directamente(self):
        cita = self.crear_cita_en_proceso()
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse('citas:cita_admin_detalle', args=[cita.id]),
            {
                'accion': 'cambiar_estado',
                'nuevo_estado': Cita.ESTADO_COMPLETADA,
                'motivo': '',
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.ESTADO_EN_PROCESO)

    def test_finalizar_rechaza_producto_repetido(self):
        cita = self.crear_cita_en_proceso()
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse('citas:cita_admin_detalle', args=[cita.id]),
            {
                'accion': 'finalizar_servicio',
                'producto_id': [str(self.producto.id), str(self.producto.id)],
                'cantidad': ['2', '1'],
                'observaciones_cierre': '',
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        cita.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertEqual(cita.estado, Cita.ESTADO_EN_PROCESO)
        self.assertEqual(self.producto.stock_actual, 10)


class TicketYCorreoCierreTests(TestCase):
    """V2SCRUM-30 (ticket PDF) y V2SCRUM-33 (correo de cierre con adjunto)."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = Usuario.objects.create_cliente(
            dui='11122233-1', password='cliente123', nombre='Laura', apellido='Reyes',
            telefono='7000-1111', email='laura@example.com', direccion='Santa Ana',
        )
        cls.admin = Usuario.objects.create_admin(
            dui='11122233-2', password='admin123', nombre='Ana', apellido='Admin',
            telefono='7000-2222', email='ana-admin@example.com',
        )
        cls.mecanico = Usuario.objects.create_mecanico(
            dui='11122233-3', password='mecanico123', nombre='Beto', apellido='Mecánico',
            telefono='7000-3333', email='beto@example.com',
            especialidad=Mecanico.ESPECIALIDAD_MECANICA_GENERAL,
        )
        cls.motocicleta = Motocicleta.objects.create(
            placa='M-7777', cliente=cls.cliente, marca='Honda', modelo='CB 190',
            anio=2022, color='Rojo',
        )
        cls.servicio = Servicio.objects.create(
            nombre='Cambio de aceite', precio_base='25.00', duracion_estimada=30,
        )

    def setUp(self):
        self.producto = Producto.objects.create(
            nombre='Aceite 10W-40', precio='9.50', stock_actual=15, stock_minimo=2,
        )

    def crear_cita_en_proceso(self):
        cita = Cita.objects.create(
            cliente=self.cliente,
            motocicleta=self.motocicleta,
            mecanico=self.mecanico,
            fecha=date.today(),
            hora=time(10, 0),
            estado=Cita.ESTADO_EN_PROCESO,
        )
        ServicioCita.objects.create(
            cita=cita, servicio=self.servicio, precio_final=self.servicio.precio_base,
        )
        return cita

    def finalizar(self, cita, **extra):
        datos = {
            'accion': 'finalizar_servicio',
            'producto_id': [str(self.producto.id)],
            'cantidad': ['2'],
            'observaciones_cierre': 'Todo en orden.',
        }
        datos.update(extra)
        self.client.force_login(self.admin)
        return self.client.post(
            reverse('citas:cita_admin_detalle', args=[cita.id]), datos,
        )

    # --- V2SCRUM-30: generación del PDF ---

    def test_generar_ticket_pdf_devuelve_bytes_con_encabezado_pdf(self):
        cita = self.crear_cita_en_proceso()
        with self.captureOnCommitCallbacks(execute=True):
            self.finalizar(cita)
        cita.refresh_from_db()

        detalle = calcular_detalle_cita(cita)
        pdf_bytes = generar_ticket_pdf(cita, detalle)

        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertGreater(len(pdf_bytes), 100)

    def test_descargar_ticket_requiere_cita_completada(self):
        cita = self.crear_cita_en_proceso()  # todavía en proceso, no completada
        self.client.force_login(self.cliente)

        respuesta = self.client.get(reverse('citas:descargar_ticket', args=[cita.id]))

        self.assertEqual(respuesta.status_code, 302)

    def test_descargar_ticket_funciona_para_cita_completada(self):
        cita = self.crear_cita_en_proceso()
        with self.captureOnCommitCallbacks(execute=True):
            self.finalizar(cita)
        cita.refresh_from_db()
        self.client.force_login(self.cliente)

        respuesta = self.client.get(reverse('citas:descargar_ticket', args=[cita.id]))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertIn(f'ticket_cita_{cita.id}.pdf', respuesta['Content-Disposition'])
        self.assertTrue(respuesta.content.startswith(b'%PDF'))

    def test_descargar_ticket_no_permite_ver_cita_de_otro_cliente(self):
        cita = self.crear_cita_en_proceso()
        with self.captureOnCommitCallbacks(execute=True):
            self.finalizar(cita)
        cita.refresh_from_db()

        otro_cliente = Usuario.objects.create_cliente(
            dui='11122233-4', password='x', nombre='Otro', apellido='Cliente',
            telefono='7000-4444', email='otro@example.com', direccion='SS',
        )
        self.client.force_login(otro_cliente)

        respuesta = self.client.get(reverse('citas:descargar_ticket', args=[cita.id]))

        self.assertEqual(respuesta.status_code, 404)