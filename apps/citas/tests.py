from datetime import date, time, timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.servicios.models import Servicio
from apps.usuarios.models import Mecanico, Usuario
from apps.vehiculos.models import Motocicleta

from .models import Cita, ServicioCita
from .services import (
    notificar_cita_agendada,
    notificar_cita_cancelada,
    notificar_cita_confirmada,
    notificar_cita_reagendada,
)


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