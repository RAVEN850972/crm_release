from django.urls import path
from . import views

urlpatterns = [
    path('', views.finance_dashboard, name='finance_dashboard'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/new/', views.transaction_new, name='transaction_new'),
    path('salary-calculation/', views.salary_calculation, name='salary_calculation'),
    path('create-salary-payment/<int:user_id>/', views.create_salary_payment, name='create_salary_payment'),
    
    # API endpoints
    path('api/stats/', views.finance_stats_api, name='finance_stats_api'),
    path('api/expense-categories/', views.expense_categories_api, name='expense_categories_api'),
]