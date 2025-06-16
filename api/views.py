from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
import openpyxl
from datetime import datetime, timedelta
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone
from decimal import Decimal

from user_accounts.models import User
from customer_clients.models import Client
from services.models import Service
from orders.models import Order, OrderItem
from finance.models import Transaction, SalaryPayment
from .serializers import (
    UserSerializer, ClientSerializer, ServiceSerializer, 
    OrderSerializer, OrderItemSerializer, TransactionSerializer, 
    SalaryPaymentSerializer
)

try:
    from salary_config.models import (
        SalaryConfig, UserSalaryAssignment, SalaryAdjustment
    )
    from salary_config.serializers import (
        SalaryConfigSerializer, UserSalaryAssignmentSerializer,
        SalaryAdjustmentSerializer, SalaryCalculationSerializer
    )
    from salary_config.services import SalaryCalculationService
    SALARY_CONFIG_AVAILABLE = True
except ImportError:
    SALARY_CONFIG_AVAILABLE = False

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['role']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    
    def get_permissions(self):
        """Права доступа в зависимости от действия"""
        if self.action in ['list', 'retrieve', 'create', 'update', 'partial_update', 'destroy']:
            # Только владелец может управлять пользователями
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Фильтрация пользователей по правам доступа"""
        if self.request.user.role == 'owner':
            return User.objects.all()
        elif self.request.user.role == 'manager':
            # Менеджер может видеть только монтажников и себя
            return User.objects.filter(
                Q(role='installer') | Q(id=self.request.user.id)
            )
        else:  # installer
            # Монтажник может видеть только себя
            return User.objects.filter(id=self.request.user.id)

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['source']
    search_fields = ['name', 'phone', 'address']
    
    def get_permissions(self):
        """Права доступа к клиентам"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Создание и редактирование только для владельца и менеджера
            if hasattr(self.request, 'user') and self.request.user.is_authenticated:
                if self.request.user.role not in ['owner', 'manager']:
                    from rest_framework.permissions import SAFE_METHODS
                    from rest_framework import permissions
                    
                    class ReadOnlyPermission(permissions.BasePermission):
                        def has_permission(self, request, view):
                            return request.method in SAFE_METHODS
                    
                    return [ReadOnlyPermission()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Фильтрация клиентов по правам доступа"""
        if not hasattr(self.request, 'user') or not self.request.user.is_authenticated:
            return Client.objects.none()
            
        if self.request.user.role == 'owner':
            return Client.objects.all()
        elif self.request.user.role == 'manager':
            # Менеджер видит всех клиентов
            return Client.objects.all()
        else:  # installer
            # Монтажник видит только клиентов из своих заказов
            return Client.objects.filter(
                order__installers=self.request.user
            ).distinct()

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category']
    search_fields = ['name']
    
    def get_permissions(self):
        """Права доступа к услугам"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Создание и редактирование только для владельца
            if hasattr(self.request, 'user') and self.request.user.is_authenticated:
                if self.request.user.role != 'owner':
                    from rest_framework.permissions import SAFE_METHODS
                    from rest_framework import permissions
                    
                    class ReadOnlyPermission(permissions.BasePermission):
                        def has_permission(self, request, view):
                            return request.method in SAFE_METHODS
                    
                    return [ReadOnlyPermission()]
        return [IsAuthenticated()]

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'manager']
    search_fields = ['client__name', 'client__phone']
    
    def get_permissions(self):
        """Права доступа к заказам"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Создание и редактирование только для владельца и менеджера
            if hasattr(self.request, 'user') and self.request.user.is_authenticated:
                if self.request.user.role not in ['owner', 'manager']:
                    from rest_framework.permissions import SAFE_METHODS
                    from rest_framework import permissions
                    
                    class ReadOnlyPermission(permissions.BasePermission):
                        def has_permission(self, request, view):
                            return request.method in SAFE_METHODS
                    
                    return [ReadOnlyPermission()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Фильтрация заказов по правам доступа"""
        if not hasattr(self.request, 'user') or not self.request.user.is_authenticated:
            return Order.objects.none()
            
        if self.request.user.role == 'owner':
            return Order.objects.all()
        elif self.request.user.role == 'manager':
            # Менеджер видит только свои заказы
            return Order.objects.filter(manager=self.request.user)
        else:  # installer
            # Монтажник видит только заказы, где он назначен
            return Order.objects.filter(installers=self.request.user)

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['type']
    search_fields = ['description']
    
    def get_permissions(self):
        """Только владелец может работать с транзакциями"""
        if hasattr(self.request, 'user') and self.request.user.is_authenticated:
            if self.request.user.role != 'owner':
                from rest_framework import permissions
                
                class OwnerOnlyPermission(permissions.BasePermission):
                    def has_permission(self, request, view):
                        return False
                
                return [OwnerOnlyPermission()]
        return [IsAuthenticated()]

class SalaryPaymentViewSet(viewsets.ModelViewSet):
    queryset = SalaryPayment.objects.all()
    serializer_class = SalaryPaymentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['user']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    
    def get_permissions(self):
        """Права доступа к зарплатам"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Создание выплат только для владельца
            if self.request.user.role != 'owner':
                from rest_framework.permissions import DenyAll
                return [DenyAll()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Фильтрация выплат по правам доступа"""
        if self.request.user.role == 'owner':
            return SalaryPayment.objects.all()
        else:
            # Другие роли видят только свои выплаты
            return SalaryPayment.objects.filter(user=self.request.user)

class FinanceBalanceView(APIView):
    """Баланс компании - только для владельца"""
    
    def get(self, request):
        if request.user.role != 'owner':
            return Response({'error': 'Нет прав доступа'}, status=403)
        
        balance = Transaction.get_company_balance()
        
        today = datetime.now()
        start_date = today.replace(day=1, month=today.month-5 if today.month > 5 else today.month+7, 
                                  year=today.year if today.month > 5 else today.year-1)
        
        transactions = Transaction.objects.filter(created_at__gte=start_date)
        monthly_data = {}
        
        for transaction in transactions:
            month_key = transaction.created_at.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {'income': 0, 'expense': 0}
            
            if transaction.type == 'income':
                monthly_data[month_key]['income'] += float(transaction.amount)
            else:
                monthly_data[month_key]['expense'] += float(transaction.amount)
        
        monthly_stats = []
        for month, data in sorted(monthly_data.items()):
            monthly_stats.append({
                'month': month,
                'income': data['income'],
                'expense': data['expense'],
                'profit': data['income'] - data['expense']
            })
        
        return Response({
            'balance': balance,
            'monthly_stats': monthly_stats
        })
    
class CalculateSalaryView(APIView):
    """Расчет зарплаты с учетом прав доступа"""
    
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        
        # Проверка прав доступа
        if request.user.role == 'owner':
            # Владелец может рассчитывать зарплату всем
            pass
        elif request.user.id == user_id:
            # Пользователь может рассчитывать свою зарплату
            pass
        else:
            return Response({'error': 'Нет прав доступа'}, status=403)
        
        # Получаем параметры дат из query string
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        # Преобразуем строки в datetime объекты
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            except ValueError:
                return Response({'error': 'Неверный формат start_date. Используйте YYYY-MM-DD'}, status=400)
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            except ValueError:
                return Response({'error': 'Неверный формат end_date. Используйте YYYY-MM-DD'}, status=400)
        
        # Расчет зарплаты в зависимости от роли
        try:
            if user.role == 'installer':
                salary = self._calculate_installer_salary(user, start_date, end_date)
            elif user.role == 'manager':
                salary = self._calculate_manager_salary(user, start_date, end_date)
            else:  # owner
                salary = self._calculate_owner_salary(start_date, end_date)
        except Exception as e:
            return Response({'error': f'Ошибка расчета зарплаты: {str(e)}'}, status=500)
            
        return Response({'salary': salary})
        
    def _calculate_installer_salary(self, user, start_date=None, end_date=None):
        from finance.utils import calculate_installer_salary
        return calculate_installer_salary(user, start_date, end_date)
        
    def _calculate_manager_salary(self, user, start_date=None, end_date=None):
        from finance.utils import calculate_manager_salary
        return calculate_manager_salary(user, start_date, end_date)
        
    def _calculate_owner_salary(self, start_date=None, end_date=None):
        from finance.utils import calculate_owner_salary
        return calculate_owner_salary(start_date, end_date)

class FinanceStatsView(APIView):
    """Расширенная финансовая статистика"""
    
    def get(self, request):
        # Текущая дата
        today = datetime.now()
        
        # Начало текущего месяца
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Доходы и расходы за текущий месяц
        income_this_month = Transaction.objects.filter(
            type='income',
            created_at__gte=start_of_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        expense_this_month = Transaction.objects.filter(
            type='expense',
            created_at__gte=start_of_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Статистика доходов/расходов по дням
        from django.db.models.functions import TruncDay
        
        # За последние 30 дней
        start_date = today - timedelta(days=30)
        
        daily_stats = Transaction.objects.filter(
            created_at__gte=start_date
        ).annotate(
            day=TruncDay('created_at')
        ).values('day', 'type').annotate(
            total=Sum('amount')
        ).order_by('day')
        
        # Преобразуем в формат, удобный для клиента
        days_data = {}
        for stat in daily_stats:
            day_str = stat['day'].strftime('%Y-%m-%d')
            if day_str not in days_data:
                days_data[day_str] = {'income': 0, 'expense': 0}
                
            days_data[day_str][stat['type']] = float(stat['total'])
        
        # Формируем список с расчетом прибыли
        daily_result = []
        for day, data in sorted(days_data.items()):
            daily_result.append({
                'date': day,
                'income': data['income'],
                'expense': data['expense'],
                'profit': data['income'] - data['expense']
            })
        
        return Response({
            'income_this_month': float(income_this_month),
            'expense_this_month': float(expense_this_month),
            'profit_this_month': float(income_this_month) - float(expense_this_month),
            'daily_stats': daily_result
        })

class DashboardStatsView(APIView):
    """Статистика дашборда с учетом роли пользователя"""
    
    def get(self, request):
        today = datetime.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if request.user.role == 'owner':
            return self._get_owner_stats(today, start_of_month)
        elif request.user.role == 'manager':
            return self._get_manager_stats(request.user, today, start_of_month)
        else:  # installer
            return self._get_installer_stats(request.user, today, start_of_month)
    
    def _get_owner_stats(self, today, start_of_month):
        """Полная статистика для владельца"""
        total_orders = Order.objects.count()
        completed_orders = Order.objects.filter(status='completed').count()
        orders_this_month = Order.objects.filter(created_at__gte=start_of_month).count()
        
        total_clients = Client.objects.count()
        clients_this_month = Client.objects.filter(created_at__gte=start_of_month).count()
        
        company_balance = Transaction.get_company_balance()
        
        income_this_month = Transaction.objects.filter(
            type='income',
            created_at__gte=start_of_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        expense_this_month = Transaction.objects.filter(
            type='expense',
            created_at__gte=start_of_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'orders_this_month': orders_this_month,
            'total_clients': total_clients,
            'clients_this_month': clients_this_month,
            'company_balance': float(company_balance),
            'income_this_month': float(income_this_month),
            'expense_this_month': float(expense_this_month),
            'role': 'owner'
        })
    
    def _get_manager_stats(self, user, today, start_of_month):
        """Статистика для менеджера"""
        manager_orders = Order.objects.filter(manager=user)
        total_orders = manager_orders.count()
        completed_orders = manager_orders.filter(status='completed').count()
        orders_this_month = manager_orders.filter(created_at__gte=start_of_month).count()
        
        total_revenue = manager_orders.filter(status='completed').aggregate(
            total=Sum('total_cost')
        )['total'] or 0
        
        return Response({
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'orders_this_month': orders_this_month,
            'total_revenue': float(total_revenue),
            'role': 'manager'
        })
    
    def _get_installer_stats(self, user, today, start_of_month):
        """Статистика для монтажника"""
        installer_orders = Order.objects.filter(installers=user)
        total_orders = installer_orders.count()
        completed_orders = installer_orders.filter(status='completed').count()
        in_progress_orders = installer_orders.filter(status='in_progress').count()
        orders_this_month = installer_orders.filter(created_at__gte=start_of_month).count()
        
        return Response({
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'in_progress_orders': in_progress_orders,
            'orders_this_month': orders_this_month,
            'role': 'installer'
        })

# Классы для экспорта данных в Excel
from .exports import export_clients_to_excel, export_orders_to_excel, export_finance_to_excel

class ExportClientsView(APIView):
    def get(self, request):
        return export_clients_to_excel()

class ExportOrdersView(APIView):
    def get(self, request):
        return export_orders_to_excel()

class ExportFinanceView(APIView):
    def get(self, request):
        return export_finance_to_excel()
    
if SALARY_CONFIG_AVAILABLE:
    class SalaryConfigViewSet(viewsets.ModelViewSet):
        """API для управления конфигурациями зарплат"""
        queryset = SalaryConfig.objects.all()
        serializer_class = SalaryConfigSerializer
        
        def get_queryset(self):
            # Только владелец может управлять конфигурациями
            if self.request.user.role != 'owner':
                return SalaryConfig.objects.none()
            return super().get_queryset()
        
        @action(detail=True, methods=['post'])
        def activate(self, request, pk=None):
            """Активация конфигурации"""
            config = self.get_object()
            
            # Деактивируем все остальные конфигурации
            SalaryConfig.objects.exclude(pk=config.pk).update(is_active=False)
            
            # Активируем выбранную
            config.is_active = True
            config.save()
            
            return Response({
                'message': f'Конфигурация "{config.name}" активирована',
                'config': SalaryConfigSerializer(config).data
            })
        
        @action(detail=True, methods=['post'])
        def copy(self, request, pk=None):
            """Копирование конфигурации"""
            source_config = self.get_object()
            new_name = request.data.get('name', f"{source_config.name} (копия)")
            
            # Создаем копию через сервис
            from salary_config.services import SalaryConfigService
            
            try:
                new_config = SalaryConfigService.copy_config(source_config, new_name)
                return Response({
                    'message': f'Конфигурация скопирована как "{new_name}"',
                    'config': SalaryConfigSerializer(new_config).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'error': f'Ошибка копирования: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)

    class UserSalaryAssignmentViewSet(viewsets.ModelViewSet):
        """API для назначений конфигураций зарплат"""
        queryset = UserSalaryAssignment.objects.all()
        serializer_class = UserSalaryAssignmentSerializer
        
        def get_queryset(self):
            # Только владелец может управлять назначениями
            if self.request.user.role != 'owner':
                return UserSalaryAssignment.objects.none()
            return super().get_queryset().select_related('user', 'config')

    class SalaryAdjustmentViewSet(viewsets.ModelViewSet):
        """API для корректировок зарплат"""
        queryset = SalaryAdjustment.objects.all()
        serializer_class = SalaryAdjustmentSerializer
        
        def get_queryset(self):
            # Только владелец может управлять корректировками
            if self.request.user.role != 'owner':
                return SalaryAdjustment.objects.none()
            return super().get_queryset().select_related('user', 'created_by')
        
        def perform_create(self, serializer):
            serializer.save(created_by=self.request.user)

    class SalaryCalculationAPIView(APIView):
        """API для расчета зарплат"""
        
        def post(self, request):
            """Расчет зарплаты для пользователя за период"""
            if request.user.role != 'owner':
                return Response({
                    'error': 'Недостаточно прав для расчета зарплат'
                }, status=status.HTTP_403_FORBIDDEN)
            
            user_id = request.data.get('user_id')
            start_date_str = request.data.get('start_date')
            end_date_str = request.data.get('end_date')
            
            if not start_date_str or not end_date_str:
                return Response({
                    'error': 'Необходимо указать start_date и end_date'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                
                # Преобразуем в datetime с временем
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())
                
                if user_id:
                    user = User.objects.get(pk=user_id)
                    
                    if user.role == 'installer':
                        result = SalaryCalculationService.calculate_installer_salary(
                            user, start_datetime, end_datetime
                        )
                    elif user.role == 'manager':
                        result = SalaryCalculationService.calculate_manager_salary(
                            user, start_datetime, end_datetime
                        )
                    elif user.role == 'owner':
                        result = SalaryCalculationService.calculate_owner_salary(
                            start_datetime, end_datetime
                        )
                    else:
                        return Response({
                            'error': 'Неизвестная роль пользователя'
                        }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # Расчет для владельца без указания пользователя
                    result = SalaryCalculationService.calculate_owner_salary(
                        start_datetime, end_datetime
                    )
                
                # Конвертируем Decimal в float для JSON
                def convert_decimals(obj):
                    if isinstance(obj, Decimal):
                        return float(obj)
                    elif isinstance(obj, dict):
                        return {k: convert_decimals(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_decimals(v) for v in obj]
                    return obj
                
                result = convert_decimals(result)
                
                return Response({
                    'success': True,
                    'data': result
                })
                
            except ValueError as e:
                return Response({
                    'error': f'Неверный формат даты: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({
                    'error': f'Ошибка расчета: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    class SalaryStatsAPIView(APIView):
        """API для статистики по зарплатам"""
        
        def get(self, request):
            """Получение статистики по зарплатам"""
            if request.user.role != 'owner':
                return Response({
                    'error': 'Недостаточно прав'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Общая статистика
            total_configs = SalaryConfig.objects.count()
            active_configs = SalaryConfig.objects.filter(is_active=True).count()
            total_assignments = UserSalaryAssignment.objects.count()
            users_without_config = User.objects.filter(
                role__in=['manager', 'installer', 'owner']
            ).exclude(
                id__in=UserSalaryAssignment.objects.values_list('user_id', flat=True)
            ).count()
            
            # Статистика корректировок за последний месяц
            from django.utils import timezone
            last_month = timezone.now() - timedelta(days=30)
            recent_adjustments = SalaryAdjustment.objects.filter(
                created_at__gte=last_month
            ).count()
            
            return Response({
                'total_configs': total_configs,
                'active_configs': active_configs,
                'total_assignments': total_assignments,
                'users_without_config': users_without_config,
                'recent_adjustments': recent_adjustments,
            })

else:
    # Заглушки, если модуль salary_config не установлен
    class SalaryConfigViewSet(viewsets.ReadOnlyModelViewSet):
        queryset = User.objects.none()
        
        def list(self, request):
            return Response({
                'error': 'Модуль настройки зарплат не установлен'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)

    class UserSalaryAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
        queryset = User.objects.none()
        
        def list(self, request):
            return Response({
                'error': 'Модуль настройки зарплат не установлен'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)

    class SalaryAdjustmentViewSet(viewsets.ReadOnlyModelViewSet):
        queryset = User.objects.none()
        
        def list(self, request):
            return Response({
                'error': 'Модуль настройки зарплат не установлен'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)

    class SalaryCalculationAPIView(APIView):
        def post(self, request):
            return Response({
                'error': 'Модуль настройки зарплат не установлен'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)

    class SalaryStatsAPIView(APIView):
        def get(self, request):
            return Response({
                'error': 'Модуль настройки зарплат не установлен'
            }, status=status.HTTP_501_NOT_IMPLEMENTED)