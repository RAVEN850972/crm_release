from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_list, name='client_list'),
    path('<int:pk>/', views.client_detail, name='client_detail'),
    path('new/', views.client_new, name='client_new'),
    path('<int:pk>/edit/', views.client_edit, name='client_edit'),
]