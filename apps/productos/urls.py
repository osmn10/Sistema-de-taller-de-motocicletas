from django.urls import path
from django.shortcuts import render

app_name = 'productos'

def inventario(request):
    return render(request, 'productos/inventario.html')

urlpatterns = [
    path('inventario/', inventario, name='inventario'),
]
