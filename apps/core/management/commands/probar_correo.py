"""Comando para verificar la configuración de correo del proyecto."""

from anymail.exceptions import AnymailAPIError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from apps.core.emails import enviar_correo_html

BACKEND_SMTP = 'django.core.mail.backends.smtp.EmailBackend'
BACKEND_BREVO = 'anymail.backends.brevo.EmailBackend'


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

        backend_smtp = settings.EMAIL_BACKEND == BACKEND_SMTP
        backend_brevo = settings.EMAIL_BACKEND == BACKEND_BREVO

        if backend_smtp and not settings.EMAIL_HOST_PASSWORD:
            raise CommandError(
                'Falta EMAIL_HOST_PASSWORD en el archivo .env. No se intentó el envío.'
            )
        if backend_brevo and not settings.ANYMAIL.get('BREVO_API_KEY'):
            raise CommandError(
                'Falta BREVO_API_KEY en el archivo .env o en Render. No se intentó el envío.'
            )

        try:
            enviado = enviar_correo_html(
                asunto='Prueba de correo - Sistema del Taller',
                plantilla='emails/prueba_conexion.html',
                contexto={},
                destinatarios=[destinatario],
                propagar_error=True,
            )
        except AnymailAPIError as error:
            raise CommandError(
                self._explicar_error_brevo(getattr(error, 'status_code', None))
            ) from None
        except Exception as error:
            raise CommandError(
                f'No se pudo enviar el correo ({type(error).__name__}). '
                'Revisa la configuración y los registros del proveedor.'
            ) from None

        if not enviado:
            raise CommandError('El backend no aceptó el correo.')

        if backend_smtp or backend_brevo:
            proveedor = 'SMTP' if backend_smtp else 'Brevo'
            resultado = (
                f'Correo aceptado por {proveedor} para {destinatario}. '
                'Comprueba su llegada a la bandeja de entrada y la carpeta de spam.'
            )
        else:
            resultado = (
                f'Prueba local completada para {destinatario}. '
                'Revisa la salida del backend; esto no acredita entrega real.'
            )
        self.stdout.write(self.style.SUCCESS(resultado))

    @staticmethod
    def _explicar_error_brevo(codigo):
        """Mensaje accionable sin exponer la respuesta cruda del proveedor."""
        if codigo == 401:
            return 'Brevo rechazó la clave (401). Revisa que BREVO_API_KEY sea la correcta.'
        if codigo == 400:
            return (
                'Brevo rechazó el mensaje (400). Revisa que el remitente esté verificado '
                'y que los datos del mensaje sean válidos.'
            )
        return (
            f'No se pudo enviar por Brevo (código {codigo or "desconocido"}). '
            'Revisa los registros del proveedor.'
        )
