/* Vista previa en centavos. El total definitivo se calcula en el servidor. */
(function () {
    'use strict';
    const form = document.getElementById('form-finalizar');
    if (!form) return;
    const filas = document.getElementById('filas-repuestos');
    const plantilla = document.getElementById('plantilla-fila-repuesto');
    const errorFinalizar = document.getElementById('error-finalizar');
    // Validamos antes de enviar para no recargar ni perder las filas ingresadas.
    form.noValidate = true;
    let intentoFinalizar = false;
    const moneda = new Intl.NumberFormat('es-SV', { style: 'currency', currency: 'USD' });
    const dinero = centavos => moneda.format(centavos / 100);
    function aCentavos(valor) {
        if (!/^\d+(\.\d{1,2})?$/.test(valor || '')) return null;
        const partes = valor.split('.');
        const resultado = Number(partes[0]) * 100 + Number((partes[1] || '').padEnd(2, '0'));
        return Number.isSafeInteger(resultado) ? resultado : null;
    }
    function actualizar() {
        const servicios = aCentavos(form.dataset.subtotalServicios);
        let valido = servicios !== null && form.dataset.preciosValidos === 'true';
        let subtotal = 0;
        let primerCampoInvalido = null;
        const vistos = new Set();
        filas.querySelectorAll('.fila-repuesto').forEach(fila => {
            const producto = fila.querySelector('select');
            const campoCantidad = fila.querySelector('input');
            const cantidadTexto = campoCantidad.value;
            const salida = fila.querySelector('.importe-repuesto');
            salida.textContent = '';
            [producto, campoCantidad].forEach(campo => {
                campo.setCustomValidity('');
                campo.removeAttribute('aria-invalid');
                campo.classList.remove('is-invalid');
            });
            producto.required = Boolean(cantidadTexto) || campoCantidad.validity.badInput;
            campoCantidad.required = Boolean(producto.value);
            if (!producto.value && !cantidadTexto && !campoCantidad.validity.badInput) return;
            const precio = aCentavos(producto.selectedOptions[0]?.dataset.precio);
            const cantidad = Number(cantidadTexto);
            const importe = precio * cantidad;
            let error = '';
            let campoInvalido = campoCantidad;
            if (!producto.value) {
                error = 'Selecciona el repuesto correspondiente a esta cantidad.';
                campoInvalido = producto;
            } else if (campoCantidad.validity.badInput) {
                error = 'Ingresa una cantidad entera mayor que cero.';
            } else if (!cantidadTexto) {
                error = 'Ingresa la cantidad del repuesto seleccionado.';
            } else if (!Number.isSafeInteger(cantidad) || cantidad <= 0) {
                error = 'La cantidad debe ser un número entero mayor que cero.';
            } else if (precio === null || !Number.isSafeInteger(importe)) {
                error = 'Revisa el precio y la cantidad del repuesto.';
            } else if (vistos.has(producto.value)) {
                error = 'Este repuesto está repetido. Usa una sola fila con la cantidad total.';
                campoInvalido = producto;
            }
            if (error) {
                valido = false;
                salida.textContent = error;
                campoInvalido.setCustomValidity(error);
                campoInvalido.setAttribute('aria-invalid', 'true');
                campoInvalido.classList.add('is-invalid');
                primerCampoInvalido = primerCampoInvalido || campoInvalido;
                return;
            }
            vistos.add(producto.value);
            subtotal += importe;
            salida.textContent = dinero(precio) + ' × ' + cantidad + ' = ' + dinero(importe);
        });
        valido = valido && Number.isSafeInteger(subtotal + servicios);
        document.getElementById('preview-repuestos').textContent = valido ? dinero(subtotal) : '—';
        document.getElementById('preview-total').textContent = valido ? dinero(servicios + subtotal) : '—';
        document.getElementById('preview-aviso').textContent = valido
            ? 'Vista previa. Al finalizar se validan el stock y los precios actuales de los repuestos.'
            : 'Completa o corrige las filas y los precios para calcular el total.';
        errorFinalizar.hidden = !intentoFinalizar || valido;
        errorFinalizar.textContent = valido ? ''
            : 'No se puede finalizar. Corrige los campos indicados; si agregas un repuesto, debes indicar su cantidad. No se ha guardado ningún cambio.';
        return { valido, primerCampoInvalido };
    }
    form.addEventListener('submit', evento => {
        intentoFinalizar = true;
        const resultado = actualizar();
        if (!resultado.valido) {
            evento.preventDefault();
            (resultado.primerCampoInvalido || errorFinalizar).focus();
            if (resultado.primerCampoInvalido) resultado.primerCampoInvalido.reportValidity();
        }
    });
    document.getElementById('btn-agregar-fila').addEventListener('click', () => {
        filas.appendChild(plantilla.content.cloneNode(true));
        actualizar();
    });
    filas.addEventListener('click', evento => {
        const boton = evento.target.closest('.btn-quitar-fila');
        if (!boton) return;
        const fila = boton.closest('.fila-repuesto');
        if (filas.querySelectorAll('.fila-repuesto').length > 1) fila.remove();
        else fila.querySelectorAll('select, input').forEach(campo => { campo.value = ''; });
        actualizar();
    });
    filas.addEventListener('input', actualizar);
    filas.addEventListener('change', actualizar);
    actualizar();
})();
