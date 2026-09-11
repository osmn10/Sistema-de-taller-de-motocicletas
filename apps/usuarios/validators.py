"""Validadores relacionados con la app usuarios.

V2SCRUM-34: política de contraseña segura reutilizable por el registro de
clientes, el restablecimiento hecho por el administrador y la recuperación
de contraseña por correo.
"""

import re


# Requisitos mínimos de una contraseña segura (V2SCRUM-34).
PASSWORD_LONGITUD_MINIMA = 8


def validar_password_segura(password):
    """Devuelve la lista de incumplimientos de la política de contraseña.

    Una lista vacía significa que la contraseña cumple la política. La función
    no lanza excepciones: el llamador decide cómo mostrar los mensajes.
    """

    errores = []
    password = password or ''

    if len(password) < PASSWORD_LONGITUD_MINIMA:
        errores.append(f'Debe tener al menos {PASSWORD_LONGITUD_MINIMA} caracteres.')
    if not re.search(r'[A-ZÁÉÍÓÚÑ]', password):
        errores.append('Debe incluir al menos una letra mayúscula.')
    if not re.search(r'[a-záéíóúñ]', password):
        errores.append('Debe incluir al menos una letra minúscula.')
    if not re.search(r'\d', password):
        errores.append('Debe incluir al menos un número.')
    if not re.search(r'[^A-Za-z0-9ÁÉÍÓÚÑáéíóúñ]', password):
        errores.append('Debe incluir al menos un símbolo (por ejemplo: !@#$%).')

    return errores
