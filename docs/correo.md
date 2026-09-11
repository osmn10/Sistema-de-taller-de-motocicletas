# V2SCRUM-28 — Servicio de envío de correo

Estado al 4 de septiembre de 2026: implementación local terminada y probada. La validación en producción queda pendiente hasta disponer del despliegue. No marcar todo el PBI como terminado si Jira exige evidencia de los tres entornos.

## Qué se agregó y cómo funciona

Las aplicaciones llaman a `enviar_correo_html` en `apps/core/emails.py`. Este módulo renderiza una plantilla, añade una versión de texto y adjuntos opcionales, y entrega el mensaje al backend de Django.

El backend decide el destino: consola para desarrollo sin envío, memoria para tests o SMTP para envío real con Resend. Se utiliza SMTP autenticado mediante una API key; no se implementó un cliente de la API HTTP de Resend. El Gmail del proyecto sirve para recibir las pruebas y administrar la cuenta; no se usa su contraseña para enviar desde Django.

La plantilla base centraliza el diseño y los datos de contacto del taller. Cada compañero puede crear una plantilla para su evento sin duplicar la conexión.

## Estado por entorno

- Desarrollo: envío real recibido por Samuel en `proyectodsi2026@gmail.com`; posteriormente confirmó que la clave reemplazada también funciona.
- Pruebas automatizadas: backend en memoria y 10 pruebas de infraestructura aprobadas, sin Internet ni credenciales.
- Pruebas desplegadas (staging): no validadas. Si este es el entorno de pruebas exigido por Jira, la suite local no sustituye su evidencia.
- Producción: configuración de correo preparada en código; instalación de variables y envío desde el servidor pendientes. No se ha validado el despliegue completo.

## Variables de entorno

Los nombres y valores públicos están en `.env.example`. La clave permanece vacía en ese archivo.

```text
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_HOST_USER=resend
RESEND_API_KEY=
EMAIL_USE_TLS=True
EMAIL_TIMEOUT=10
DEFAULT_FROM_EMAIL=Sistema del Taller <onboarding@resend.dev>
TALLER_NOMBRE=Sistema del Taller
TALLER_TELEFONO=
TALLER_DIRECCION=
TALLER_EMAIL_CONTACTO=
```

- `EMAIL_BACKEND`: consola, memoria o SMTP. Para envío real establecer `django.core.mail.backends.smtp.EmailBackend`.
- `RESEND_API_KEY`: credencial secreta utilizada como contraseña SMTP; no colocar la contraseña de Gmail.
- `DEFAULT_FROM_EMAIL`: remitente autorizado por el proveedor.
- Las variables `TALLER_*` personalizan la firma. No inventar datos de contacto; los campos opcionales vacíos no se muestran.

No subir `.env`, claves, capturas de credenciales ni respuestas crudas del proveedor al repositorio. Cada entorno con envío real debe utilizar su propia clave, preferiblemente con permiso de envío únicamente. Las pruebas en memoria y consola no requieren cuenta ni clave de Resend.

## Cómo probar en otra computadora

1. Instalar las dependencias del proyecto en su entorno virtual.
2. Crear `.env` a partir de `.env.example` solo si no existe; no sobrescribir uno existente.
3. Mantener el backend de consola para trabajar sin credenciales.
4. Ejecutar desde la raíz del proyecto:

```bash
.venv/bin/python manage.py probar_correo proyectodsi2026@gmail.com
.venv/bin/python manage.py test apps.core --settings=config.settings.testing
```

En Windows sustituir `.venv/bin/python` por `.venv\Scripts\python.exe`. En consola, el primer comando solo muestra el mensaje: no envía nada. Los tests fuerzan memoria aunque el `.env` local seleccione SMTP.

Para una prueba real, configurar SMTP y la clave en el `.env` personal, y ejecutar el mismo comando de prueba. La aceptación SMTP no garantiza entrega: comprobar el buzón y el registro del proveedor. Con el remitente de prueba `onboarding@resend.dev`, usar el correo de la cuenta; para enviar a otros destinatarios se requiere un dominio propio verificado.

Si aparece `CERTIFICATE_VERIFY_FAILED` con Python instalado desde python.org en macOS, revisar su instalación de certificados. No desactivar la verificación TLS.

## Cómo integrar una notificación

```python
from apps.core.emails import enviar_correo_html

aceptado = enviar_correo_html(
    asunto='Prueba de conexión',
    plantilla='emails/prueba_conexion.html',
    contexto={},
    destinatarios=['cliente@example.com'],
)
```

El ejemplo usa una plantilla existente y un destinatario ficticio. Para un evento real, crear su propia plantilla heredando de `emails/base.html`, preparar su contexto y llamar al módulo desde el servicio de la aplicación, no duplicar credenciales en una vista.

Para adjuntar un PDF ya generado, añadir `adjuntos=[('ticket.pdf', contenido_pdf_en_bytes, 'application/pdf')]`. Este módulo transporta el archivo; no genera el ticket ni calcula montos.

Cuando el evento modifica la base de datos, programar su notificación con `transaction.on_commit` para evitar enviar antes de confirmar la transacción. El envío sigue siendo síncrono: no se añadió una cola de tareas.

La función devuelve `True` cuando el backend acepta un mensaje. Ante errores de renderizado o envío, registra el tipo de error sin la respuesta cruda y devuelve `False` por defecto. El llamador debe decidir cómo informar o registrar el fallo. No hay reintentos automáticos ni historial persistente de notificaciones. `propagar_error=True` queda reservado para diagnóstico.

## Evidencia de pruebas

Las 10 pruebas de infraestructura cubren: comando de prueba, destinatario inválido, falta de clave SMTP, redacción de errores del proveedor, contenido HTML/texto, transporte de adjunto PDF, backend que devuelve cero, plantilla inexistente, destinatarios vacíos y error de envío.

La suite conjunta de `apps.core` y `apps.citas` tiene 14 pruebas aprobadas. Las cuatro de citas corresponden a otro PBI y no equivalen a validación manual completa de sus pantallas.

## Pendiente cuando exista hosting

1. Configurar `DJANGO_SETTINGS_MODULE=config.settings.production`.
2. Configurar explícitamente `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` y las variables SMTP anteriores desde el panel seguro del hosting.
3. Utilizar una clave exclusiva de producción y un remitente autorizado. Verificar dominio para destinatarios reales.
4. Completar también los requisitos generales del despliegue: base PostgreSQL y su controlador, `DATABASE_URL`, `SECRET_KEY` segura y `ALLOWED_HOSTS`. No quedaron validados por las pruebas de correo locales.
5. Verificar que el hosting permite salida SMTP con TLS. Si la bloquea, evaluar la integración HTTP como cambio adicional.
6. Ejecutar la prueba desde el servidor desplegado y verificar recepción; guardar entorno, fecha y evidencia sin secretos.
7. Repetir en staging si se exige un ambiente desplegado de pruebas.

## Archivos para un commit exclusivo de V2SCRUM-28

Seleccionar únicamente estos archivos; no se ha realizado commit ni staging:

```text
.env.example
config/settings/base.py
config/settings/development.py
config/settings/production.py
config/settings/testing.py
apps/core/emails.py
apps/core/tests.py
apps/core/management/commands/probar_correo.py
apps/core/templates/emails/base.html
apps/core/templates/emails/prueba_conexion.html
docs/correo.md
```

Excluir de este commit `apps/citas/services.py`, `apps/citas/views.py`, `apps/citas/tests.py` y `apps/core/templates/emails/citas/`: son la implementación local de V2SCRUM-31 (agendar/confirmar). No seleccionar toda la carpeta de emails indiscriminadamente.

Mensaje sugerido: `feat(V2SCRUM-28): configurar correo y pruebas por entorno`.

Antes de confirmar cambios, revisar la selección y comprobar que `git ls-files .env` no devuelve rutas y que `git check-ignore .env` indica que está ignorado. El archivo real `.env` nunca forma parte de la selección.
