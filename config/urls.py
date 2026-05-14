"""
URL configuration for config project.

Cada app interna expone su propio urls.py con app_name. Aquí solo se hacen
los include() y se montan los archivos estáticos/media en desarrollo.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls', namespace='core')),
    path('usuarios/', include('apps.usuarios.urls', namespace='usuarios')),
    path('vehiculos/', include('apps.vehiculos.urls', namespace='vehiculos')),
    path('servicios/', include('apps.servicios.urls', namespace='servicios')),
    path('productos/', include('apps.productos.urls', namespace='productos')),
    path('citas/', include('apps.citas.urls', namespace='citas')),
    path('configuracion/', include('apps.configuracion.urls', namespace='configuracion')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
