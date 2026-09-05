from io import StringIO
from unittest.mock import patch
from smtplib import SMTPAuthenticationError

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from apps.core.emails import enviar_correo_html


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='Sistema del Taller <onboarding@resend.dev>',
)
class ProbarCorreoCommandTests(SimpleTestCase):
    def test_envia_un_correo_de_prueba(self):
        salida = StringIO()

        call_command('probar_correo', 'destinatario@example.com', stdout=salida)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['destinatario@example.com'])
        self.assertEqual(
            mail.outbox[0].subject,
            'Prueba de correo - Sistema del Taller',
        )
        self.assertIn('Prueba local completada', salida.getvalue())

    def test_rechaza_un_destinatario_invalido(self):
        with self.assertRaisesMessage(CommandError, 'correo válido'):
            call_command('probar_correo', 'correo-invalido')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST_PASSWORD='',
    )
    @patch('apps.core.management.commands.probar_correo.enviar_correo_html')
    def test_sin_clave_no_intenta_smtp(self, enviar):
        with self.assertRaisesMessage(CommandError, 'Falta RESEND_API_KEY'):
            call_command('probar_correo', 'cliente@example.com')
        enviar.assert_not_called()

    @patch('apps.core.management.commands.probar_correo.enviar_correo_html')
    def test_error_del_comando_no_expone_respuesta_del_proveedor(self, enviar):
        enviar.side_effect = SMTPAuthenticationError(535, b'secreto-simulado')
        with self.assertRaises(CommandError) as resultado:
            call_command('probar_correo', 'cliente@example.com')
        self.assertNotIn('secreto-simulado', str(resultado.exception))
        self.assertIn('SMTPAuthenticationError', str(resultado.exception))


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='Sistema del Taller <onboarding@resend.dev>',
    TALLER_NOMBRE='Taller de prueba',
    TALLER_TELEFONO='2222-2222',
    TALLER_DIRECCION='San Salvador',
    TALLER_EMAIL_CONTACTO='contacto@example.com',
)
class EnviarCorreoHtmlTests(SimpleTestCase):
    def test_renderiza_plantilla_html_y_version_texto(self):
        enviado = enviar_correo_html(
            asunto='Mensaje de prueba',
            plantilla='emails/prueba_conexion.html',
            contexto={},
            destinatarios=['cliente@example.com'],
        )

        self.assertTrue(enviado)
        self.assertEqual(len(mail.outbox), 1)
        mensaje = mail.outbox[0]
        self.assertEqual(mensaje.to, ['cliente@example.com'])
        self.assertIn('Conexión exitosa', mensaje.body)
        contenido_html, tipo_mime = mensaje.alternatives[0]
        self.assertEqual(tipo_mime, 'text/html')
        self.assertIn('Taller de prueba', contenido_html)

    def test_adjunta_pdf_sin_alterar_nombre_tipo_ni_bytes(self):
        # Datos binarios de transporte; no es una prueba del generador de PDF.
        contenido = b'%PDF-1.4\n%fixture-binario\n\x00\xff\n%%EOF'
        enviado = enviar_correo_html(
            asunto='Comprobante',
            plantilla='emails/prueba_conexion.html',
            contexto={},
            destinatarios=['cliente@example.com'],
            adjuntos=[('ticket.pdf', contenido, 'application/pdf')],
        )
        self.assertTrue(enviado)
        mensaje = mail.outbox[0]
        adjuntos = list(mensaje.message().get_payload())[1:]
        self.assertEqual(len(adjuntos), 1)
        self.assertEqual(adjuntos[0].get_filename(), 'ticket.pdf')
        self.assertEqual(adjuntos[0].get_content_type(), 'application/pdf')
        self.assertEqual(adjuntos[0].get_payload(decode=True), contenido)

    @patch('apps.core.emails.EmailMultiAlternatives.send', return_value=0)
    def test_registra_cuando_backend_no_acepta_mensaje(self, enviar):
        with self.assertLogs('apps.core.emails', level='ERROR') as registro:
            enviado = enviar_correo_html(
                asunto='Cita #12', plantilla='emails/prueba_conexion.html',
                contexto={}, destinatarios=['cliente@example.com'],
            )
        self.assertFalse(enviado)
        self.assertIn('Cita #12', registro.output[0])

    @patch('apps.core.emails.EmailMultiAlternatives.send')
    def test_plantilla_inexistente_no_interrumpe_operacion(self, enviar):
        with self.assertLogs('apps.core.emails', level='ERROR'):
            resultado = enviar_correo_html(
                asunto='Prueba', plantilla='emails/no_existe.html',
                contexto={}, destinatarios=['cliente@example.com'],
            )
        self.assertFalse(resultado)
        enviar.assert_not_called()

    @patch('apps.core.emails.EmailMultiAlternatives.send')
    def test_sin_destinatarios_no_intenta_envio(self, enviar):
        with self.assertLogs('apps.core.emails', level='WARNING'):
            resultado = enviar_correo_html(
                asunto='Prueba', plantilla='emails/prueba_conexion.html',
                contexto={}, destinatarios=[' '],
            )
        self.assertFalse(resultado)
        enviar.assert_not_called()

    @patch('apps.core.emails.EmailMultiAlternatives.send')
    def test_captura_el_error_sin_interrumpir_el_negocio(self, enviar):
        enviar.side_effect = RuntimeError('secreto-simulado')

        with self.assertLogs('apps.core.emails', level='ERROR') as registro:
            enviado = enviar_correo_html(
                asunto='Mensaje de prueba',
                plantilla='emails/prueba_conexion.html',
                contexto={},
                destinatarios=['cliente@example.com'],
            )

        self.assertFalse(enviado)
        self.assertIn('RuntimeError', registro.output[0])
        self.assertNotIn('secreto-simulado', registro.output[0])
