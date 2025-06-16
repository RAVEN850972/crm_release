from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('<int:pk>/', views.order_detail, name='order_detail'),
    path('new/', views.order_new, name='order_new'),
    path('<int:pk>/edit/', views.order_edit, name='order_edit'),
    path('<int:pk>/add-item/', views.order_add_item, name='order_add_item'),
    path('<int:pk>/change-status/', views.order_change_status, name='order_change_status'),
    path('my-orders/', views.my_orders, name='my_orders'),
]