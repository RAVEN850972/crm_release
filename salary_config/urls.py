# salary_config/urls.py
from django.urls import path
from . import views

app_name = 'salary_config'

urlpatterns = [
    # Конфигурации зарплат
    path('', views.salary_config_list, name='config_list'),
    path('config/<int:pk>/', views.salary_config_detail, name='config_detail'),
    path('config/create/', views.salary_config_create, name='config_create'),
    path('config/<int:pk>/edit/', views.salary_config_edit, name='config_edit'),
    path('config/copy/', views.salary_config_copy, name='config_copy'),
    
    # Назначения
    path('assignments/', views.salary_assignments, name='assignments'),
    path('assignments/create/', views.salary_assignment_create, name='assignment_create'),
    path('assignments/<int:pk>/edit/', views.salary_assignment_edit, name='assignment_edit'),
    path('assignments/<int:pk>/delete/', views.salary_assignment_delete, name='assignment_delete'),
    path('assignments/bulk/', views.bulk_salary_assignment, name='bulk_assignment'),
    
    # Корректировки
    path('adjustments/', views.salary_adjustments, name='adjustments'),
    path('adjustments/create/', views.salary_adjustment_create, name='adjustment_create'),
    path('adjustments/<int:pk>/edit/', views.salary_adjustment_edit, name='adjustment_edit'),
    
    # Расчеты
    path('calculation/', views.salary_calculation_view, name='calculation'),
    
    # API
    path('api/auto-assign/', views.auto_assign_default_config, name='auto_assign'),
    path('api/calculate/', views.salary_calculation_api, name='calculation_api'),
]