# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, ClientViewSet, ServiceViewSet, OrderViewSet,
    TransactionViewSet, SalaryPaymentViewSet,
    FinanceBalanceView, CalculateSalaryView, DashboardStatsView, FinanceStatsView,
    ExportClientsView, ExportOrdersView, ExportFinanceView,
    # Импорты для зарплат
    SalaryConfigViewSet, UserSalaryAssignmentViewSet, SalaryAdjustmentViewSet,
    SalaryCalculationAPIView, SalaryStatsAPIView
)
from .modal import (
    ModalClientDataView, ModalOrderDataView, ModalOrderItemDataView,
    ModalTransactionDataView, ModalSalaryPaymentDataView
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'clients', ClientViewSet)
router.register(r'services', ServiceViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'salary-payments', SalaryPaymentViewSet)

# Маршруты для настройки зарплат
router.register(r'salary-configs', SalaryConfigViewSet)
router.register(r'salary-assignments', UserSalaryAssignmentViewSet)
router.register(r'salary-adjustments', SalaryAdjustmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    
    # Статистика и дашборды
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    
    # Финансы
    path('finance/balance/', FinanceBalanceView.as_view(), name='finance-balance'),
    path('finance/stats/', FinanceStatsView.as_view(), name='finance-stats'),
    path('finance/calculate-salary/<int:user_id>/', CalculateSalaryView.as_view(), name='calculate-salary'),
    
    # API для зарплат
    path('salary/calculate/', SalaryCalculationAPIView.as_view(), name='salary-calculate'),
    path('salary/stats/', SalaryStatsAPIView.as_view(), name='salary-stats'),
    
    # Экспорт
    path('export/clients/', ExportClientsView.as_view(), name='export-clients'),
    path('export/orders/', ExportOrdersView.as_view(), name='export-orders'),
    path('export/finance/', ExportFinanceView.as_view(), name='export-finance'),

    # Модальные окна
    path('modal/client/', ModalClientDataView.as_view(), name='modal-client-create'),
    path('modal/client/<int:client_id>/', ModalClientDataView.as_view(), name='modal-client-edit'),
    path('modal/order/', ModalOrderDataView.as_view(), name='modal-order-create'),
    path('modal/order/<int:order_id>/', ModalOrderDataView.as_view(), name='modal-order-edit'),
    path('modal/order/<int:order_id>/items/', ModalOrderItemDataView.as_view(), name='modal-order-item-add'),
    path('modal/order/<int:order_id>/items/<int:item_id>/', ModalOrderItemDataView.as_view(), name='modal-order-item-delete'),
    path('modal/transaction/', ModalTransactionDataView.as_view(), name='modal-transaction-create'),
    path('modal/transaction/<int:transaction_id>/', ModalTransactionDataView.as_view(), name='modal-transaction-edit'),
    path('modal/salary-payment/<int:user_id>/', ModalSalaryPaymentDataView.as_view(), name='modal-salary-payment'),
    
    # Календарь и маршрутизация
    path('calendar/', include('calendar_app.urls')),
]