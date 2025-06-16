from django.urls import path
from . import views

urlpatterns = [
    path('', views.service_list, name='service_list'),
    path('<int:pk>/', views.service_detail, name='service_detail'),
    path('new/', views.service_new, name='service_new'),
    path('<int:pk>/edit/', views.service_edit, name='service_edit'),
]