from django.test import TestCase
from django.urls import reverse

from apps.usuarios.models import Usuario

from .models import Producto, Proveedor


class ProveedoresTests(TestCase):
    """CRUD de proveedores y su asociación con productos (uno a muchos)."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_admin(
            dui='22222222-2',
            password='admin123',
            nombre='Alex',
            apellido='Admin',
            telefono='7000-2222',
            email='admin@example.com',
        )
        cls.cliente = Usuario.objects.create_cliente(
            dui='11111111-1',
            password='cliente123',
            nombre='Ana',
            apellido='López',
            telefono='7000-1111',
            email='ana@example.com',
            direccion='San Miguel',
        )

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse('productos:proveedores')

    def guardar(self, **datos):
        return self.client.post(self.url, {'accion': 'guardar', **datos})

    def test_crear_proveedor(self):
        self.guardar(nombre='Repuestos del Oriente', telefono='2660-1234', email='ventas@oriente.com')

        proveedor = Proveedor.objects.get()
        self.assertEqual(proveedor.nombre, 'Repuestos del Oriente')
        self.assertEqual(proveedor.telefono, '2660-1234')
        self.assertEqual(proveedor.email, 'ventas@oriente.com')
        self.assertTrue(proveedor.activo)

    def test_telefono_y_correo_son_opcionales(self):
        self.guardar(nombre='MotoPartes', telefono='', email='')

        self.assertTrue(Proveedor.objects.filter(nombre='MotoPartes').exists())

    def test_crear_requiere_nombre(self):
        self.guardar(nombre='', telefono='2660-1234', email='')

        self.assertFalse(Proveedor.objects.exists())

    def test_no_permite_nombre_repetido(self):
        Proveedor.objects.create(nombre='MotoPartes')

        self.guardar(nombre='motopartes')

        self.assertEqual(Proveedor.objects.count(), 1)

    def test_rechaza_telefono_con_formato_invalido(self):
        self.guardar(nombre='MotoPartes', telefono='12345')

        self.assertFalse(Proveedor.objects.exists())

    def test_rechaza_correo_invalido(self):
        self.guardar(nombre='MotoPartes', email='no-es-correo')

        self.assertFalse(Proveedor.objects.exists())

    def test_editar_proveedor(self):
        proveedor = Proveedor.objects.create(nombre='MotoPartes', telefono='2225-6789')

        self.guardar(proveedor_id=proveedor.id, nombre='MotoPartes SV', telefono='2225-0000', email='')

        proveedor.refresh_from_db()
        self.assertEqual(proveedor.nombre, 'MotoPartes SV')
        self.assertEqual(proveedor.telefono, '2225-0000')

    def test_desactivar_y_activar_proveedor(self):
        proveedor = Proveedor.objects.create(nombre='MotoPartes')

        self.client.post(self.url, {'accion': 'desactivar', 'proveedor_id': proveedor.id})
        proveedor.refresh_from_db()
        self.assertFalse(proveedor.activo)

        self.client.post(self.url, {'accion': 'activar', 'proveedor_id': proveedor.id})
        proveedor.refresh_from_db()
        self.assertTrue(proveedor.activo)

    def test_solo_el_admin_gestiona_proveedores(self):
        self.client.force_login(self.cliente)

        respuesta = self.guardar(nombre='Intruso')

        self.assertRedirects(respuesta, reverse('core:home'), fetch_redirect_response=False)
        self.assertFalse(Proveedor.objects.exists())

    def test_un_proveedor_tiene_varios_productos(self):
        proveedor = Proveedor.objects.create(nombre='MotoPartes')

        for nombre in ['Bujía', 'Filtro de aire']:
            self.client.post(reverse('productos:crear_producto'), {
                'nombre': nombre,
                'precio': '5.00',
                'stock_actual': '10',
                'stock_minimo': '2',
                'proveedor': proveedor.id,
            })

        self.assertEqual(proveedor.productos.count(), 2)

    def test_editar_producto_conserva_su_proveedor_desactivado(self):
        proveedor = Proveedor.objects.create(nombre='MotoPartes', activo=False)
        producto = Producto.objects.create(
            nombre='Bujía', precio='3.50', stock_actual=10, stock_minimo=2, proveedor=proveedor,
        )

        self.client.post(reverse('productos:editar_producto', args=[producto.id]), {
            'nombre': 'Bujía estándar',
            'precio': '3.50',
            'stock_actual': '10',
            'stock_minimo': '2',
            'proveedor': proveedor.id,
        })

        producto.refresh_from_db()
        self.assertEqual(producto.nombre, 'Bujía estándar')
        self.assertEqual(producto.proveedor, proveedor)

    def test_no_permite_asignar_un_proveedor_desactivado_a_un_producto_nuevo(self):
        proveedor = Proveedor.objects.create(nombre='MotoPartes', activo=False)

        self.client.post(reverse('productos:crear_producto'), {
            'nombre': 'Bujía',
            'precio': '3.50',
            'stock_actual': '10',
            'stock_minimo': '2',
            'proveedor': proveedor.id,
        })

        self.assertFalse(Producto.objects.filter(nombre='Bujía').exists())
