from django.urls import path
from django.shortcuts import render
app_name = 'configuracion'
def horario(request):
    return render(request, 'configuracion/horario.html')
urlpatterns = [
    path('horario/', horario, name='horario'),
]
