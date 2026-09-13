/*
 * Mostrar / ocultar contraseña en cualquier campo type="password".
 *
 * Uso: envolver el <input type="password" id="xxx"> en un .input-group
 * junto al botón de core/_pw_toggle_boton.html (con data-pw-toggle="xxx").
 */

(function () {
    function alternar(boton) {
        var input = document.getElementById(boton.dataset.pwToggle);
        if (!input) { return; }
        var oculto = input.type === 'password';
        input.type = oculto ? 'text' : 'password';
        var ojo = boton.querySelector('[data-pw-eye]');
        var ojoTachado = boton.querySelector('[data-pw-eye-slash]');
        if (ojo) { ojo.hidden = oculto; }
        if (ojoTachado) { ojoTachado.hidden = !oculto; }
        boton.setAttribute('aria-pressed', oculto ? 'true' : 'false');
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-pw-toggle]').forEach(function (boton) {
            boton.addEventListener('click', function () { alternar(boton); });
        });
    });
})();
