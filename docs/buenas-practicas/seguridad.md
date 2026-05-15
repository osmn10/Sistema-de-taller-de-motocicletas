# Seguridad de la información

Esta guía describe qué información no debe versionarse, compartirse en chats
públicos ni subirse al repositorio, para evitar filtrar datos personales del
equipo o credenciales del proyecto.

## Qué nunca se sube al repositorio

| Archivo / dato | Por qué |
| -------------- | ------- |
| `.env` | Contiene la `SECRET_KEY` real y, en producción, credenciales de base de datos. |
| `db.sqlite3` | Contiene datos locales de prueba que pueden incluir información de usuarios reales si se hacen pruebas con datos verdaderos. |
| Carpeta `venv/` | Específica de cada máquina; ocupa MB innecesarios y no aporta nada al historial. |
| `__pycache__/`, `*.pyc` | Bytecode generado automáticamente. |
| Archivos del editor (`.vscode/`, `.idea/`) | Configuración personal de cada desarrollador. |
| `.DS_Store`, `Thumbs.db` | Metadata del sistema operativo. |
| Capturas de pantalla con datos reales | Pueden contener correos, contraseñas autocompletadas o tokens visibles en la barra del navegador. |
| Archivos con credenciales (`*.pem`, `*.key`, `credentials.json`) | Cualquier llave o certificado privado. |

Todas estas reglas ya están aplicadas en el archivo `.gitignore`. **Antes de
hacer un `git add .` revisar siempre `git status` para confirmar que solo se
está agregando lo que corresponde.**

## Manejo de variables de entorno

- El archivo `.env.example` se versiona (con valores de ejemplo, nunca reales).
- El archivo `.env` se mantiene local. Cada integrante tiene el suyo.
- Si una variable cambia (se agrega una nueva clave, por ejemplo), actualizar
  `.env.example` con el nombre y un valor placeholder, y avisar al equipo.

### Cómo generar una `SECRET_KEY` segura

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Esa clave va en el `.env` local, nunca en el código fuente ni en mensajes de
chat compartidos.

## Manejo de contraseñas y credenciales

- **No compartir contraseñas por chat ni por correo en texto plano.** Si hay
  que pasar credenciales temporales (acceso a un servidor de pruebas, por
  ejemplo), usar un gestor de contraseñas o algún canal cifrado y rotar la
  clave después.
- Las contraseñas de los superusuarios locales son responsabilidad de cada
  integrante. No reutilizar contraseñas personales.
- En producción, las credenciales viajan únicamente por variables de entorno
  del servidor.

## Datos personales del equipo

- No incluir correos personales, números de teléfono, direcciones, fotos ni
  documentos de identidad en archivos del repositorio.
- Si para documentación se necesita listar al equipo, usar únicamente nombre
  y carnet académico, y mantener esa información fuera de archivos que se
  vayan a publicar como demo o que se compartan fuera del curso.

## Antes de hacer push

Checklist mínimo:

- [ ] `git status` no muestra archivos sospechosos (`.env`, `db.sqlite3`, `venv/`).
- [ ] Ningún archivo nuevo tiene contraseñas, llaves o tokens escritos a mano.
- [ ] Las capturas de pantalla, si hay, no contienen información sensible.
- [ ] El mensaje de commit es descriptivo y no expone información privada.

## Si una credencial se filtró por error

1. Considerar la credencial como comprometida. Cambiarla de inmediato (rotar
   `SECRET_KEY`, contraseñas, tokens, etc.).
2. Reescribir el historial **no es suficiente**: si el repositorio ya fue
   clonado por alguien más, la credencial ya está afuera. La única solución
   real es rotar la credencial.
3. Avisar al equipo y dejar constancia en el canal interno.
