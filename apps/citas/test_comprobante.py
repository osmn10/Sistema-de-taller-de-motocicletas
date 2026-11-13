"""Pruebas de V2SCRUM-36: comprobante PDF de cita agendada."""

import base64
import re
import zlib
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse

from apps.servicios.models import Servicio
from apps.usuarios.models import Usuario
from apps.vehiculos.models import Motocicleta

from .comprobante_pdf import generar_comprobante_pdf, numero_comprobante
from .models import Cita, ServicioCita


class ComprobanteCitaTests(TestCase):
    """Criterios de aceptación de V2SCRUM-36 (datos ficticios)."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = Usuario.objects.create_cliente(
            dui='22233344-1', password='cliente123', nombre='Marta', apellido='Prueba',
            telefono='7100-1111', email='marta.prueba@example.com', direccion='San Miguel',
        )
        cls.otro_cliente = Usuario.objects.create_cliente(
            dui='22233344-2', password='cliente123', nombre='Otro', apellido='Cliente',
            telefono='7100-2222', email='otro.cliente@example.com', direccion='San Salvador',
        )
        cls.admin = Usuario.objects.create_admin(
            dui='22233344-3', password='admin123', nombre='Ana', apellido='Admin',
            telefono='7100-3333', email='ana.admin@example.com',
        )
        cls.moto = Motocicleta.objects.create(
            placa='M-4321', cliente=cls.cliente, marca='Yamaha', modelo='FZ 150',
            anio=2021, color='Azul',
        )
        cls.servicio = Servicio.objects.create(
            nombre='Afinado general', precio_base='30.00', duracion_estimada=60,
        )

    def crear_cita(self, estado='pendiente'):
        cita = Cita.objects.create(
            cliente=self.cliente, motocicleta=self.moto,
            fecha=date.today() + timedelta(days=3), hora=time(9, 0), estado_id=estado,
        )
        ServicioCita.objects.create(cita=cita, servicio=self.servicio, precio_final='30.00')
        return cita

    def url(self, cita):
        return reverse('citas:descargar_comprobante', args=[cita.id])

    # --- Criterio 1: PDF con fecha, hora, servicios y motocicleta ---

    def test_genera_pdf_valido(self):
        pdf = generar_comprobante_pdf(self.crear_cita())
        self.assertTrue(pdf.startswith(b'%PDF'))

    def test_pdf_contiene_datos_de_la_reserva(self):
        cita = self.crear_cita()
        texto = _texto_pdf(generar_comprobante_pdf(cita))
        self.assertIn(cita.fecha.strftime('%d/%m/%Y'), texto)
        self.assertIn('09:00', texto)
        self.assertIn('Afinado general', texto)
        self.assertIn('M-4321', texto)

    def test_cliente_descarga_comprobante_de_cita_recien_agendada(self):
        cita = self.crear_cita()
        self.client.force_login(self.cliente)
        respuesta = self.client.get(self.url(cita))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF'))

    # --- Criterio 2: identificador único ---

    def test_cada_comprobante_tiene_identificador_unico(self):
        cita_1 = self.crear_cita()
        cita_2 = self.crear_cita()
        self.assertNotEqual(numero_comprobante(cita_1), numero_comprobante(cita_2))
        self.assertIn(numero_comprobante(cita_1), _texto_pdf(generar_comprobante_pdf(cita_1)))

        self.client.force_login(self.cliente)
        respuesta = self.client.get(self.url(cita_1))
        self.assertIn(numero_comprobante(cita_1), respuesta['Content-Disposition'])

    # --- Criterio 3: sigue disponible desde el detalle ---

    def test_detalle_de_cita_muestra_boton_de_comprobante(self):
        cita = self.crear_cita(estado='confirmada')
        self.client.force_login(self.cliente)
        respuesta = self.client.get(reverse('citas:cita_detalle', args=[cita.id]))
        self.assertContains(respuesta, self.url(cita))

    def test_comprobante_disponible_en_cita_completada(self):
        cita = self.crear_cita(estado='completada')
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(self.url(cita)).status_code, 200)

    def test_cita_cancelada_no_entrega_comprobante(self):
        cita = self.crear_cita(estado='cancelada')
        self.client.force_login(self.cliente)
        respuesta = self.client.get(self.url(cita))
        self.assertRedirects(respuesta, reverse('citas:cita_detalle', args=[cita.id]))
        detalle = self.client.get(reverse('citas:cita_detalle', args=[cita.id]))
        self.assertNotContains(detalle, self.url(cita))

    # --- Control de acceso ---

    def test_otro_cliente_no_puede_descargar_comprobante_ajeno(self):
        cita = self.crear_cita()
        self.client.force_login(self.otro_cliente)
        self.assertEqual(self.client.get(self.url(cita)).status_code, 404)

    def test_usuario_sin_sesion_es_enviado_al_login(self):
        cita = self.crear_cita()
        respuesta = self.client.get(self.url(cita))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('usuarios:login'), respuesta['Location'])

    def test_admin_no_usa_la_descarga_del_cliente(self):
        cita = self.crear_cita()
        self.client.force_login(self.admin)
        respuesta = self.client.get(self.url(cita))
        self.assertRedirects(respuesta, reverse('core:home'), fetch_redirect_response=False)


def _texto_pdf(pdf_bytes):
    """Extrae el texto de un PDF de reportlab (flujos ASCII85 + Flate) sin librerías extra."""
    texto = []
    for flujo in re.findall(rb'stream\r?\n(.*?)endstream', pdf_bytes, re.S):
        try:
            flujo = zlib.decompress(base64.a85decode(flujo.strip(), adobe=True))
        except (ValueError, zlib.error):
            continue
        texto.extend(re.findall(rb'\((.*?)\)\s*Tj', flujo))
    return b' '.join(texto).decode('latin-1')
