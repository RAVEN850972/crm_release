from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db.models.functions import TruncMonth, TruncDay

from customer_clients.models import Client
from orders.models import Order
from services.models import Service
from user_accounts.models import User

# Проверяем доступность модели Transaction
try:
    from finance.models import Transaction
    FINANCE_AVAILABLE = True
except ImportError:
    FINANCE_AVAILABLE = False
    Transaction = None

@login_required
def dashboard(request):
    """Главный дашборд с показателями в зависимости от роли пользователя"""
    today = timezone.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    context = {
        'user_role': request.user.role,
        'user_name': request.user.get_full_name() or request.user.username,
    }
    
    # Контент для владельца - полная статистика
    if request.user.role == 'owner':
        context.update(_get_owner_dashboard_data(today, start_of_month))
    
    # Контент для менеджера - статистика по его заказам
    elif request.user.role == 'manager':
        context.update(_get_manager_dashboard_data(request.user, today, start_of_month))
    
    # Контент для монтажника - только его заказы
    else:  # installer
        context.update(_get_installer_dashboard_data(request.user, today, start_of_month))
    
    return render(request, 'dashboard/dashboard.html', context)

def _get_owner_dashboard_data(today, start_of_month):
    """Данные дашборда для владельца"""
    # Статистика по заказам
    total_orders = Order.objects.count()
    completed_orders = Order.objects.filter(status='completed').count()
    orders_this_month = Order.objects.filter(created_at__gte=start_of_month).count()
    
    # Статистика по клиентам
    total_clients = Client.objects.count()
    clients_this_month = Client.objects.filter(created_at__gte=start_of_month).count()
    
    # Финансовые показатели (если доступны)
    company_balance = Decimal('0.00')
    income_this_month = Decimal('0.00')
    expenses_this_month = Decimal('0.00')
    
    if FINANCE_AVAILABLE and Transaction:
        try:
            company_balance = Transaction.get_company_balance()
            
            income_this_month = Transaction.objects.filter(
                type='income',
                created_at__gte=start_of_month
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            expenses_this_month = Transaction.objects.filter(
                type='expense',
                created_at__gte=start_of_month
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        except:
            pass
    
    # Заказы по месяцам
    orders_by_month = get_orders_by_month(months=6)
    
    # Источники клиентов
    clients_by_source_data = get_clients_by_source()
    clients_by_source = []
    for item in clients_by_source_data:
        source_display = dict(Client.SOURCE_CHOICES).get(item['source'], item['source'])
        clients_by_source.append({
            'source': item['source'],
            'source_display': source_display,
            'count': item['count']
        })
    
    # Топ менеджеры
    top_managers = get_top_managers(limit=5)
    
    # Последние заказы
    recent_orders = Order.objects.all().order_by('-created_at')[:5]
    
    return {
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'orders_this_month': orders_this_month,
        'total_clients': total_clients,
        'clients_this_month': clients_this_month,
        'company_balance': company_balance,
        'income_this_month': income_this_month,
        'expenses_this_month': expenses_this_month,
        'orders_by_month': orders_by_month,
        'clients_by_source': clients_by_source,
        'top_managers': top_managers,
        'recent_orders': recent_orders,
        'show_full_stats': True,
    }

def _get_manager_dashboard_data(user, today, start_of_month):
    """Данные дашборда для менеджера"""
    # Статистика по заказам менеджера
    manager_orders = Order.objects.filter(manager=user)
    total_orders = manager_orders.count()
    completed_orders = manager_orders.filter(status='completed').count()
    orders_this_month = manager_orders.filter(created_at__gte=start_of_month).count()
    
    # Выручка от заказов менеджера
    total_revenue = manager_orders.filter(status='completed').aggregate(
        total=Sum('total_cost')
    )['total'] or Decimal('0.00')
    
    revenue_this_month = manager_orders.filter(
        status='completed',
        completed_at__gte=start_of_month
    ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')
    
    # Последние заказы менеджера
    recent_orders = manager_orders.order_by('-created_at')[:5]
    
    # Расчет зарплаты менеджера (если доступен)
    salary_data = None
    try:
        from finance.utils import calculate_manager_salary
        salary_data = calculate_manager_salary(user, start_of_month, today)
    except ImportError:
        pass
    
    # Клиенты менеджера (через заказы)
    manager_clients = Client.objects.filter(
        order__manager=user
    ).distinct().count()
    
    return {
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'orders_this_month': orders_this_month,
        'total_revenue': total_revenue,
        'revenue_this_month': revenue_this_month,
        'manager_clients': manager_clients,
        'recent_orders': recent_orders,
        'salary_data': salary_data,
        'show_manager_stats': True,
    }

def _get_installer_dashboard_data(user, today, start_of_month):
    """Данные дашборда для монтажника"""
    # Статистика по заказам монтажника
    installer_orders = Order.objects.filter(installers=user)
    total_orders = installer_orders.count()
    completed_orders = installer_orders.filter(status='completed').count()
    in_progress_orders = installer_orders.filter(status='in_progress').count()
    orders_this_month = installer_orders.filter(created_at__gte=start_of_month).count()
    
    # Последние заказы монтажника
    recent_orders = installer_orders.order_by('-created_at')[:5]
    
    # Расчет зарплаты монтажника (если доступен)
    salary_data = None
    try:
        from finance.utils import calculate_installer_salary
        salary_data = calculate_installer_salary(user, start_of_month, today)
    except ImportError:
        pass
    
    return {
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'in_progress_orders': in_progress_orders,
        'orders_this_month': orders_this_month,
        'recent_orders': recent_orders,
        'salary_data': salary_data,
        'show_installer_stats': True,
    }

def get_clients_by_source():
    """Получение статистики клиентов по источникам"""
    return Client.objects.values('source').annotate(count=Count('id'))

def get_orders_by_month(months=6):
    """Получение статистики заказов по месяцам"""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30 * months)
    
    return Order.objects.filter(
        created_at__range=(start_date, end_date)
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id'),
        revenue=Sum('total_cost')
    ).order_by('month')

def get_top_managers(limit=5):
    """Получение топ менеджеров по продажам"""
    return Order.objects.filter(
        status='completed'
    ).values(
        'manager__id', 'manager__first_name', 'manager__last_name'
    ).annotate(
        orders_count=Count('id'),
        revenue=Sum('total_cost')
    ).order_by('-revenue')[:limit]