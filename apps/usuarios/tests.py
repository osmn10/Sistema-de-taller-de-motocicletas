"""Tests de la app usuarios.

Cubren la política de contraseña segura y el flujo de recuperación de
contraseña por correo (V2SCRUM-34).
"""

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.usuarios.models import Cliente
from apps.usuarios.validators import validar_password_segura


class PoliticaPasswordTests(TestCase):
    """La política exige longitud, mayúscula, minúscula, número y símbolo."""

    def test_password_valida_no_devuelve_errores(self):
        self.assertEqual(validar_password_segura('Abcdef1$'), [])

    def test_password_corta_falla(self):
        self.assertTrue(any('8 caracteres' in e for e in validar_password_segura('Ab1$')))

    def test_password_sin_mayuscula_falla(self):
        self.assertTrue(any('mayúscula' in e for e in validar_password_segura('abcdefg1$')))

    def test_password_sin_minuscula_falla(self):
        self.assertTrue(any('minúscula' in e for e in validar_password_segura('ABCDEFG1$')))

    def test_password_sin_numero_falla(self):
        self.assertTrue(any('número' in e for e in validar_password_segura('Abcdefg$')))

    def test_password_sin_simbolo_falla(self):
        self.assertTrue(any('símbolo' in e for e in validar_password_segura('Abcdefg1')))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RecuperacionPasswordTests(TestCase):
    """Flujo completo de recuperación por correo."""

    def setUp(self):
        self.cliente = Cliente(
            dui='12345678-9', nombre='Ana', apellido='Reyes',
            telefono='7777-7777', email='ana@example.com', direccion='San Salvador',
        )
        self.cliente.set_password('ClaveVieja1$')
        self.cliente.save()

    def _enlace_valido(self):
        uid = urlsafe_base64_encode(force_bytes(self.cliente.pk))
        token = default_token_generator.make_token(self.cliente)
        return reverse(
            'usuarios:password_reset_confirmar',
            kwargs={'uidb64': uid, 'token': token},
        )

    def test_solicitud_con_correo_existente_envia_email(self):
        resp = self.client.post(
            reverse('usuarios:password_reset_solicitar'),
            {'identificador': 'ana@example.com'},
        )
        self.assertRedirects(resp, reverse('usuarios:login'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('ana@example.com', mail.outbox[0].to)

    def test_solicitud_con_dui_existente_envia_email(self):
        resp = self.client.post(
            reverse('usuarios:password_reset_solicitar'),
            {'identificador': '12345678-9'},
        )
        self.assertRedirects(resp, reverse('usuarios:login'))
        self.assertEqual(len(mail.outbox), 1)

    def test_solicitud_con_cuenta_inexistente_no_envia_ni_revela(self):
        resp = self.client.post(
            reverse('usuarios:password_reset_solicitar'),
            {'identificador': 'nadie@example.com'},
        )
        self.assertRedirects(resp, reverse('usuarios:login'))
        self.assertEqual(len(mail.outbox), 0)

    def test_dui_bien_formado_inexistente_sigue_generico(self):
        resp = self.client.post(
            reverse('usuarios:password_reset_solicitar'),
            {'identificador': '99999999-9'},
        )
        self.assertRedirects(resp, reverse('usuarios:login'))
        self.assertEqual(len(mail.outbox), 0)

    def test_dui_mal_formado_muestra_error_de_formato(self):
        resp = self.client.post(
            reverse('usuarios:password_reset_solicitar'),
            {'identificador': '123'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'formato')
        self.assertEqual(len(mail.outbox), 0)

    def test_correo_mal_formado_muestra_error_de_formato(self):
        resp = self.client.post(
            reverse('usuarios:password_reset_solicitar'),
            {'identificador': 'ana@correo'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'formato')
        self.assertEqual(len(mail.outbox), 0)

    def test_campo_vacio_muestra_error(self):
        resp = self.client.post(
            reverse('usuarios:password_reset_solicitar'),
            {'identificador': ''},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_confirmar_cambia_password_y_notifica(self):
        resp = self.client.post(
            self._enlace_valido(),
            {'contrasena': 'ClaveNueva9#', 'confirmar': 'ClaveNueva9#'},
        )
        self.assertRedirects(resp, reverse('usuarios:login'))
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.check_password('ClaveNueva9#'))
        self.assertEqual(len(mail.outbox), 1)

    def test_confirmar_rechaza_password_insegura(self):
        resp = self.client.post(
            self._enlace_valido(),
            {'contrasena': 'insegura', 'confirmar': 'insegura'},
        )
        self.assertEqual(resp.status_code, 200)
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.check_password('ClaveVieja1$'))

    def test_confirmar_rechaza_si_no_coinciden(self):
        resp = self.client.post(
            self._enlace_valido(),
            {'contrasena': 'ClaveNueva9#', 'confirmar': 'Otra9#Cosa'},
        )
        self.assertEqual(resp.status_code, 200)
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.check_password('ClaveVieja1$'))

    def test_token_invalido_redirige_a_solicitar(self):
        url = reverse(
            'usuarios:password_reset_confirmar',
            kwargs={'uidb64': 'xxx', 'token': 'token-invalido'},
        )
        resp = self.client.get(url)
        self.assertRedirects(resp, reverse('usuarios:password_reset_solicitar'))

    def test_token_no_se_puede_reutilizar(self):
        url = self._enlace_valido()
        self.client.post(url, {'contrasena': 'ClaveNueva9#', 'confirmar': 'ClaveNueva9#'})
        resp = self.client.get(url)
        self.assertRedirects(resp, reverse('usuarios:password_reset_solicitar'))
