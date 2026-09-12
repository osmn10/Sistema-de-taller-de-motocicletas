from datetime import date, time
from decimal import Decimal

from django.test import RequestFactory, TestCase
from django.http import Http404
from django.urls import reverse

from apps.productos.models import Producto
from apps.servicios.models import Servicio
from apps.usuarios.models import Usuario
from apps.vehiculos.models import Motocicleta
from .models import Cita, RepuestoUsado, ServicioCita
from .totales import calcular_detalle_cita, precio_valido
from .views import cita_admin_detalle, cita_detalle


class TotalesCitaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_admin(
            dui='77777777-7', password='test', nombre='Admin', apellido='Prueba',
            telefono='7000-0000', email='admin-total@example.com',
        )
        cls.cliente = Usuario.objects.create_cliente(
            dui='88888888-8', password='test', nombre='Cliente', apellido='Prueba',
            telefono='7000-0001', email='cliente-total@example.com', direccion='San Miguel',
        )
        cls.moto = Motocicleta.objects.create(
            placa='M-8888', cliente=cls.cliente, marca='Honda', modelo='Prueba', anio=2024,
        )
        cls.servicio = Servicio.objects.create(nombre='Servicio', precio_base='15.00', duracion_estimada=30)

    def setUp(self):
        self.cita = Cita.objects.create(
            cliente=self.cliente, motocicleta=self.moto, fecha=date.today(), hora=time(9),
            estado=Cita.ESTADO_EN_PROCESO,
        )
        ServicioCita.objects.create(cita=self.cita, servicio=self.servicio, precio_final='15.00')
        self.producto = Producto.objects.create(nombre='Filtro', precio='4.25', stock_actual=10)
        self.client.force_login(self.admin)
        self.url = reverse('citas:cita_admin_detalle', args=[self.cita.id])

    def cerrar(self, **extra):
        datos = {'accion': 'finalizar_servicio', 'producto_id': [str(self.producto.id)], 'cantidad': ['2']}
        datos.update(extra)
        return self.client.post(self.url, datos)

    def ver_detalle(self):
        # Render real, sin el recolector de contextos de Client (Django #35844,
        # incompatibilidad de copy(Context) de Django 5.1 con Python 3.14).
        request = RequestFactory().get(self.url)
        request.user = self.admin
        return cita_admin_detalle(request, self.cita.id)

    def test_suma_servicios_y_cantidad_por_precio(self):
        otro = Servicio.objects.create(nombre='Otro', precio_base='10.10', duracion_estimada=15)
        ServicioCita.objects.create(cita=self.cita, servicio=otro, precio_final='10.10')
        self.cerrar()
        detalle = calcular_detalle_cita(self.cita)
        self.assertEqual(detalle['subtotal_servicios'], Decimal('25.10'))
        self.assertEqual(detalle['subtotal_repuestos'], Decimal('8.50'))
        self.assertEqual(detalle['total'], Decimal('33.60'))
        self.assertEqual(detalle['repuestos'][0]['importe'], Decimal('8.50'))

    def test_cierre_guarda_precio_y_no_confia_en_total_del_navegador(self):
        self.cerrar(total='0.01', precio_unitario='0.01')
        usado = self.cita.repuestos_usados.get()
        self.assertEqual(usado.precio_unitario, Decimal('4.25'))
        self.assertEqual(calcular_detalle_cita(self.cita)['total'], Decimal('23.50'))

    def test_cambios_de_catalogo_no_alteran_cita_cerrada(self):
        self.cerrar()
        Producto.objects.filter(pk=self.producto.pk).update(precio='99.00')
        Servicio.objects.filter(pk=self.servicio.pk).update(precio_base='99.00')
        self.assertEqual(calcular_detalle_cita(self.cita)['total'], Decimal('23.50'))

    def test_sin_repuestos_suma_solo_servicios(self):
        self.cerrar(producto_id=[''], cantidad=[''])
        self.assertEqual(calcular_detalle_cita(self.cita)['total'], Decimal('15.00'))

    def test_suma_varios_productos(self):
        aceite = Producto.objects.create(nombre='Aceite', precio='8.10', stock_actual=5)
        self.cerrar(producto_id=[str(self.producto.id), str(aceite.id)], cantidad=['2', '1'])
        self.assertEqual(calcular_detalle_cita(self.cita)['total'], Decimal('31.60'))

    def test_precios_cero_son_validos(self):
        Producto.objects.filter(pk=self.producto.pk).update(precio='0.00')
        self.cerrar()
        self.assertEqual(calcular_detalle_cita(self.cita)['total'], Decimal('15.00'))

    def test_consumo_anterior_se_muestra_referencial_no_como_cobro(self):
        RepuestoUsado.objects.create(cita=self.cita, producto=self.producto, cantidad=2)
        detalle = calcular_detalle_cita(self.cita)
        self.assertTrue(detalle['es_referencial'])
        self.assertIsNone(detalle['total'])
        self.assertEqual(detalle['total_referencia'], Decimal('23.50'))
        respuesta = self.ver_detalle()
        self.assertContains(respuesta, 'Total referencial')
        self.assertContains(respuesta, 'no confirma lo cobrado')
        self.assertIsNone(self.cita.repuestos_usados.get().precio_unitario)

    def test_detalle_renderiza_precios_importes_y_total(self):
        self.cerrar()
        respuesta = self.ver_detalle()
        self.assertContains(respuesta, 'Subtotal de servicios')
        self.assertContains(respuesta, 'Subtotal de repuestos')
        self.assertContains(respuesta, 'Filtro')
        self.assertContains(respuesta, '23,50')
        self.assertNotContains(respuesta, 'Total referencial')

    def test_formulario_incluye_precios_sin_localizacion_para_preview(self):
        respuesta = self.ver_detalle()
        self.assertContains(respuesta, 'data-precio="4.25"')
        self.assertContains(respuesta, 'data-subtotal-servicios="15.00"')
        self.assertContains(respuesta, 'citas/js/detalle_total.js')

    def test_repetir_cierre_no_duplica_consumo_ni_stock(self):
        self.cerrar()
        self.cerrar()
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, 8)
        self.assertEqual(self.cita.repuestos_usados.count(), 1)
        self.assertEqual(calcular_detalle_cita(self.cita)['total'], Decimal('23.50'))

    def test_precio_negativo_impide_finalizar_sin_descontar(self):
        Producto.objects.filter(pk=self.producto.pk).update(precio='-1.00')
        self.cerrar()
        self.cita.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.ESTADO_EN_PROCESO)
        self.assertEqual(self.producto.stock_actual, 10)
        self.assertFalse(self.cita.repuestos_usados.exists())

    def test_precio_servicio_invalido_impide_finalizar(self):
        self.cita.serviciocita_set.update(precio_final='-1.00')
        self.cerrar()
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.ESTADO_EN_PROCESO)
        self.assertIsNone(calcular_detalle_cita(self.cita)['total'])

    def test_filas_incompletas_no_se_descartan_silenciosamente(self):
        self.cerrar(producto_id=[str(self.producto.id)], cantidad=[])
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.ESTADO_EN_PROCESO)
        self.assertFalse(self.cita.repuestos_usados.exists())

    def test_validacion_de_precio(self):
        for valor in (None, '', 'NaN', 'Infinity', '-0.01'):
            with self.subTest(valor=valor):
                self.assertFalse(precio_valido(valor))

    def test_cliente_no_puede_consultar_detalle_administrativo(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def ver_detalle_cliente(self, usuario=None):
        request = RequestFactory().get(reverse('citas:cita_detalle', args=[self.cita.id]))
        request.user = usuario or self.cliente
        return cita_detalle(request, self.cita.id)

    def test_cliente_ve_mismo_desglose_al_completar(self):
        self.cerrar()
        respuesta = self.ver_detalle_cliente()
        for texto in ('Detalle y total del servicio', 'Filtro', 'Cantidad',
                      'Precio unitario', 'Subtotal de servicios', 'Subtotal de repuestos', '23,50'):
            self.assertContains(respuesta, texto)
        self.assertNotContains(respuesta, 'Finalizar servicio')
        self.assertNotContains(respuesta, 'CAMBIAR ESTADO')

    def test_cliente_no_ve_total_antes_de_completar(self):
        respuesta = self.ver_detalle_cliente()
        self.assertNotContains(respuesta, 'Total general')
        self.assertNotContains(respuesta, 'Repuestos e insumos utilizados')

    def test_cliente_no_puede_ver_importes_de_otra_persona(self):
        otro = Usuario.objects.create_cliente(
            dui='99999999-9', password='test', nombre='Otro', apellido='Cliente',
            telefono='7000-0002', email='otro-total@example.com', direccion='San Miguel',
        )
        self.cerrar()
        with self.assertRaises(Http404):
            self.ver_detalle_cliente(otro)

    def test_cliente_ve_advertencia_en_cita_sin_precio_historico(self):
        RepuestoUsado.objects.create(cita=self.cita, producto=self.producto, cantidad=2)
        self.cita.estado = Cita.ESTADO_COMPLETADA
        self.cita.save(update_fields=['estado'])
        respuesta = self.ver_detalle_cliente()
        self.assertContains(respuesta, 'Total referencial')
        self.assertContains(respuesta, 'no confirma lo cobrado')
