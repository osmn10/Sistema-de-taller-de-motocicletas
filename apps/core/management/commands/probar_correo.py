"""Comando para verificar la configuración de correo del proyecto."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from apps.core.emails import enviar_correo_html


class Command(BaseCommand):
    help = 'Envía un correo de prueba al destinatario indicado.'

    def add_arguments(self, parser):
        parser.add_argument(
            'destinatario',
            help='Dirección que recibirá el correo de prueba.',
        )

    def handle(self, *args, **options):
        destinatario = options['destinatario'].strip()

        try:
            validate_email(destinatario)
        except ValidationError as error:
            raise CommandError('Debes indicar un correo válido.') from error

        backend_smtp = (
            settings.EMAIL_BACKEND
            == 'django.core.mail.backends.smtp.EmailBackend'
        )
        if backend_smtp and not settings.EMAIL_HOST_PASSWORD:
            raise CommandError(
                'Falta RESEND_API_KEY en el archivo .env. No se intentó el envío.'
            )

        try:
            enviado = enviar_correo_html(
                asunto='Prueba de correo - Sistema del Taller',
                plantilla='emails/prueba_conexion.html',
                contexto={},
                destinatarios=[destinatario],
                propagar_error=True,
            )
        except Exception as error:
            raise CommandError(
                f'No se pudo enviar el correo ({type(error).__name__}). '
                'Revisa la configuración y los registros del proveedor.'
            ) from None

        if not enviado:
            raise CommandError('El backend no aceptó el correo.')

        if backend_smtp:
            resultado = (
                f'Correo aceptado por SMTP para {destinatario}. '
                'Comprueba su llegada a la bandeja de entrada.'
            )
        else:
            resultado = (
                f'Prueba local completada para {destinatario}. '
                'Revisa la salida del backend; esto no acredita entrega real.'
            )
        self.stdout.write(
            self.style.SUCCESS(resultado)
        )
