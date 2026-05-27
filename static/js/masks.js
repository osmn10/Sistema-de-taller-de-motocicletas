/*
 * Máscaras automáticas para inputs con data-mask.
 *
 * Uso:
 *   <input type="text" data-mask="dui"      maxlength="10">
 *   <input type="text" data-mask="telefono" maxlength="9">
 *   <input type="text" data-mask="placa"    maxlength="6">
 *   <input type="text" data-mask="nit"      maxlength="17">
 */

(function () {
    const MASCARAS_DIGITOS = {
        dui:      { posicionesGuion: [8],         maxDigitos: 9 },
        telefono: { posicionesGuion: [4],         maxDigitos: 8 },
        nit:      { posicionesGuion: [4, 10, 13], maxDigitos: 14 },
    };

    function aplicarMascaraDigitos(input, config) {
        let valor = input.value.replace(/\D/g, '');
        valor = valor.slice(0, config.maxDigitos);

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
        let digitos = input.value.replace(/\D/g, '').slice(0, 4);
        input.value = digitos ? 'M-' + digitos : '';
    }

    function manejarInput(event) {
        const input = event.target;
        const tipo = input.dataset.mask;

        if (tipo === 'placa') {
            aplicarMascaraPlaca(input);
        } else if (MASCARAS_DIGITOS[tipo]) {
            aplicarMascaraDigitos(input, MASCARAS_DIGITOS[tipo]);
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const inputs = document.querySelectorAll('input[data-mask]');
        inputs.forEach(function (input) {
            input.addEventListener('input', manejarInput);
            if (input.value) {
                manejarInput({ target: input });
            }
        });
    });
})();
