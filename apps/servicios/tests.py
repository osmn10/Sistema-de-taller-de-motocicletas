"""Tests de la app servicios."""

from django.test import TestCase
from django.urls import reverse

from apps.servicios.models import Servicio
from apps.usuarios.models import Usuario


class CatalogoServiciosTests(TestCase):
    """HU018-CP003: no pueden existir dos servicios con el mismo nombre."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_admin(
            dui='22222222-2', password='admin123', nombre='Alex', apellido='Admin',
            telefono='7000-2222', email='admin@example.com',
        )
        cls.servicio = Servicio.objects.create(
            nombre='Lavado de motor', precio_base=12, duracion_estimada=45,
        )

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse('servicios:catalogo')

    def guardar(self, nombre, servicio_id=''):
        # El formulario se envía a la misma URL desde la que se abrió (como en el navegador).
        consulta = f'?editar={servicio_id}' if servicio_id else '?mostrar_form=1'
        return self.client.post(self.url + consulta, {
            'accion': 'guardar', 'servicio_id': servicio_id, 'nombre': nombre,
            'descripcion': '', 'precio_base': '12.00', 'duracion_estimada': '45',
        })

    def test_no_crea_servicio_con_nombre_repetido(self):
        resp = self.guardar('lavado de MOTOR')

        self.assertContains(resp, 'Ya existe un servicio con ese nombre.')
        self.assertEqual(Servicio.objects.count(), 1)

    def test_editar_conservando_su_propio_nombre_si_se_permite(self):
        resp = self.guardar('Lavado de motor', servicio_id=self.servicio.id)

        self.assertRedirects(resp, self.url)

    def test_editar_con_el_nombre_de_otro_servicio_no_se_permite(self):
        otro = Servicio.objects.create(nombre='Cambio de aceite', precio_base=10, duracion_estimada=30)

        resp = self.guardar('Lavado de motor', servicio_id=otro.id)

        self.assertContains(resp, 'Ya existe un servicio con ese nombre.')
        otro.refresh_from_db()
        self.assertEqual(otro.nombre, 'Cambio de aceite')
