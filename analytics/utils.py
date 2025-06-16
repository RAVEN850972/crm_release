from django.db.models import Count, Sum, Avg, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone
from datetime import timedelta
from customer_clients.models import Client  # Исправлено с clients.models
from orders.models import Order, OrderItem
from services.models import Service
from finance.models import Transaction, SalaryPayment  # Исправлено с analytics.models

def get_clients_by_source():
    """Получение статистики клиентов по источникам"""
    return Client.objects.values('source').annotate(count=Count('id'))

def get_orders_by_status():
    """Получение статистики заказов по статусам"""
    return Order.objects.values('status').annotate(count=Count('id'))

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

def get_services_by_category():
    """Получение статистики услуг по категориям"""
    return OrderItem.objects.values(
        'service__category'
    ).annotate(
        count=Count('id'),
        revenue=Sum('price')
    ).order_by('-revenue')

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

def get_profit_by_day(days=30):
    """Получение данных о прибыли по дням"""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Расчет прибыли (цена продажи - себестоимость)
    order_items = OrderItem.objects.filter(
        order__completed_at__range=(start_date, end_date),
        order__status='completed'
    ).annotate(
        day=TruncDay('order__completed_at'),
        profit=ExpressionWrapper(F('price') - F('service__cost_price'), output_field=DecimalField())
    ).values('day').annotate(
        total_profit=Sum('profit'),
        revenue=Sum('price')
    ).order_by('day')
    
    return order_items