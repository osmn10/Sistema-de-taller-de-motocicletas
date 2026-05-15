# Buenas prácticas de desarrollo

Convenciones del equipo para mantener el código consistente, las ramas
ordenadas y el historial limpio.

## Flujo de Git

### Reglas básicas

- **Rama principal: `main`.** Solo se integra código que funciona y que ya
  pasó por revisión.
- **Una rama por funcionalidad o por bug.** Nunca trabajar directo sobre
  `main`.
- **Sincronizar antes de empezar.** Hacer `git pull` antes de crear una rama
  nueva o antes de retomar el trabajo del día.

### Nombres de rama

Usar prefijos para identificar el tipo de trabajo:

| Prefijo | Para qué |
| ------- | -------- |
| `feature/` | Nueva funcionalidad. Ej: `feature/registro-cliente`. |
| `fix/` | Corrección de un bug. Ej: `fix/error-login-mecanico`. |
| `refactor/` | Reorganización de código sin cambiar comportamiento. |
| `docs/` | Cambios solo en documentación. |

Usar minúsculas y guiones, sin tildes ni espacios.

### Mensajes de commit

- Escribir en español, en imperativo, breves y específicos.
- Una línea de máximo ~70 caracteres como título; si hace falta más detalle,
  agregar una línea en blanco y luego el cuerpo del mensaje.

Ejemplos:

```
Agregar formulario de registro de cliente
Corregir validación del número de placa
Reorganizar las urls de la app citas
Actualizar README con guía de instalación
```

Evitar mensajes genéricos como `cambios`, `update`, `arreglos varios`,
`commit final`.

### Antes de hacer push

```bash
git status                       # confirmar qué se va a subir
git diff --staged                # revisar línea por línea
python manage.py check           # validar configuración
python manage.py test            # correr los tests (si hay)
```

### Pull requests

- Cada rama de funcionalidad se integra a `main` mediante Pull Request.
- El PR debe describir qué cambia y por qué.
- Otra persona del equipo revisa antes de hacer merge.
- Después del merge, borrar la rama remota.

## Estilo de código Python

- Seguir **PEP 8**: 4 espacios de indentación, líneas de máximo 99
  caracteres, una línea en blanco entre métodos.
- Nombres en `snake_case` para variables y funciones, `PascalCase` para
  clases.
- Imports ordenados en tres bloques separados por línea en blanco:
  1. Librería estándar de Python (`import os`, `from datetime import ...`).
  2. Librerías de terceros (`from django.db import ...`).
  3. Módulos locales del proyecto (`from apps.usuarios.models import ...`).

### Comentarios y docstrings

- Solo comentar lo que **no es obvio** mirando el código.
- Las funciones públicas y los modelos llevan docstring breve explicando el
  propósito.
- No dejar comentarios tipo `# TODO` sin responsable. Si se deja un TODO,
  indicar quién lo va a tomar o crear una tarea en el tablero del equipo.

## Convenciones del proyecto Django

### Apps

- Cada app vive en `apps/<nombre>/` y se referencia como `apps.<nombre>` en
  `INSTALLED_APPS`.
- El `AppConfig` de cada app define `label` y `verbose_name` en español.

### Modelos

- Usar nombres en singular y en `PascalCase` (`Cliente`, `Motocicleta`,
  `OrdenServicio`).
- Definir `class Meta` con `verbose_name` y `verbose_name_plural` en
  español.
- Implementar `__str__` para que el panel admin muestre algo legible.

### URLs

- Cada app tiene su `urls.py` con `app_name = '<nombre>'`.
- En `config/urls.py` se incluyen con `namespace='<nombre>'`.
- Las URLs usan nombres descriptivos: `name='cliente-detalle'`,
  no `name='detalle'`.

### Templates

- Cada app tiene sus templates en `apps/<nombre>/templates/<nombre>/`.
- Todas las plantillas extienden de `core/base.html`.
- Bloques estándar: `{% block title %}`, `{% block content %}`,
  `{% block extra_css %}`, `{% block extra_js %}`.

### Migraciones

- Generar migraciones después de cada cambio en `models.py`:
  `python manage.py makemigrations <app>`.
- Revisar el archivo de migración generado antes de hacer commit.
- Nunca editar a mano una migración ya aplicada en `main`.

## Trabajo en equipo

- **Antes de empezar a trabajar en una funcionalidad nueva**, avisar en el
  canal del equipo para evitar que dos personas hagan lo mismo.
- **Si un cambio toca código compartido** (modelos en `core`, settings,
  urls principales), comunicarlo antes de hacer push.
- **Si se rompe `main`**, prioridad máxima del equipo es repararlo antes de
  seguir con otras tareas.

## Checklist antes de pedir revisión

- [ ] El código corre sin errores localmente.
- [ ] Las migraciones están al día.
- [ ] El servidor de desarrollo levanta y la funcionalidad se probó en el
      navegador.
- [ ] No hay credenciales ni datos sensibles en los archivos modificados.
- [ ] Los commits tienen mensajes descriptivos.
- [ ] La rama está actualizada con `main`.
