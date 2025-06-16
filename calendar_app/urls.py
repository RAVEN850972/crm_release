# calendar_app/urls.py - минимальная версия без сложных зависимостей

from django.urls import path
from django.http import JsonResponse

# Временная заглушка для календаря
def calendar_placeholder(request):
    return JsonResponse({
        'message': 'Календарь монтажей в разработке',
        'status': 'placeholder'
    })

urlpatterns = [
    path('', calendar_placeholder, name='calendar_placeholder'),
]