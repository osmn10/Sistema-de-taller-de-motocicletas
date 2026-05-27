/*
 * Máscaras automáticas para inputs con data-mask.
 *
 * Uso en cualquier template:
 *   <input type="text" data-mask="dui"      maxlength="10">
 *   <input type="text" data-mask="telefono" maxlength="9">
 *   <input type="text" data-mask="placa"    maxlength="6">
 *   <input type="text" data-mask="nit"      maxlength="17">
 *
 * El usuario solo digita dígitos (y la M en placa). El script va
 * insertando los guiones en las posiciones correctas mientras escribe.
 *
 * Va envuelto en una IIFE (función anónima auto-ejecutada) para no
 * contaminar el scope global con variables y funciones nuestras.
 */

(function () {
    // Cada tipo de máscara tiene dos cosas:
    //   - posicionesGuion: índices (en la cadena de solo dígitos) ANTES de
    //     los cuales hay que meter un guión. Ej: DUI tiene guión antes del
    //     dígito en posición 8 (el último).
    //   - maxDigitos: cuántos dígitos máximo permite (sin contar guiones).
    const MASCARAS_DIGITOS = {
        dui:      { posicionesGuion: [8],         maxDigitos: 9 },
        telefono: { posicionesGuion: [4],         maxDigitos: 8 },
        nit:      { posicionesGuion: [4, 10, 13], maxDigitos: 14 },
    };

    function aplicarMascaraDigitos(input, config) {
        // /\D/g = todo lo que NO es dígito → lo borro.
        let valor = input.value.replace(/\D/g, '');
        // Corto si pasó el máximo (igual el atributo maxlength lo limita en UI).
        valor = valor.slice(0, config.maxDigitos);

        // Recorro dígito por dígito y voy armando el resultado:
        // si la posición actual está en la lista de guiones, meto un "-" antes.
        let resultado = '';
        for (let i = 0; i < valor.length; i++) {
            if (config.posicionesGuion.includes(i)) {
                resultado += '-';
            }
            resultado += valor[i];
        }
        input.value = resultado;
    }

    function aplicarMascaraPlaca(input) {
        // Formato: M-#### (la M va fija, el usuario solo digita los 4 dígitos).
        let digitos = input.value.replace(/\D/g, '').slice(0, 4);
        input.value = digitos ? 'M-' + digitos : '';
    }

    // Esta es la función que se ejecuta CADA VEZ que el usuario escribe
    // un caracter en el input. event.target es el input mismo.
    function manejarInput(event) {
        const input = event.target;
        const tipo = input.dataset.mask;  // viene del atributo data-mask del HTML

        if (tipo === 'placa') {
            aplicarMascaraPlaca(input);
        } else if (MASCARAS_DIGITOS[tipo]) {
            aplicarMascaraDigitos(input, MASCARAS_DIGITOS[tipo]);
        }
    }

    // Esperar a que el DOM esté listo y enganchar el evento "input" en
    // cada <input> que tenga el atributo data-mask.
    document.addEventListener('DOMContentLoaded', function () {
        const inputs = document.querySelectorAll('input[data-mask]');
        inputs.forEach(function (input) {
            input.addEventListener('input', manejarInput);
            // Si el input ya trae un valor (por ejemplo cuando el form se
            // muestra de nuevo con errores), normalizo ese valor también.
            if (input.value) {
                manejarInput({ target: input });
            }
        });
    });
})();
