# salary_config/services.py
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone
from typing import Dict, Optional

from user_accounts.models import User
from orders.models import Order, OrderItem
from .models import (
    SalaryConfig, ManagerSalaryConfig, InstallerSalaryConfig, 
    OwnerSalaryConfig, UserSalaryAssignment, SalaryAdjustment,
)
from finance.models import SalaryPayment

def _parse_date_param(date_param):
    """Вспомогательная функция для парсинга параметров даты"""
    if date_param is None:
        return None
    if isinstance(date_param, str):
        try:
            # Парсим строку и делаем datetime объект timezone-aware
            dt = datetime.strptime(date_param, '%Y-%m-%d')
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        except ValueError:
            return None
    if hasattr(date_param, 'date'):
        # Если это datetime объект, убеждаемся что он timezone-aware
        return timezone.make_aware(date_param) if timezone.is_naive(date_param) else date_param
    return date_param

class SalaryCalculationService:
    """Сервис для расчета зарплат с учетом настроек"""
    
    @staticmethod
    def get_user_salary_config(user: User) -> Optional[SalaryConfig]:
        """Получает конфигурацию зарплаты для пользователя"""
        try:
            assignment = UserSalaryAssignment.objects.get(user=user)
            if assignment.config.is_active:
                return assignment.config
        except UserSalaryAssignment.DoesNotExist:
            pass
        
        # Если нет персональной конфигурации, ищем активную по умолчанию
        try:
            return SalaryConfig.objects.filter(
                is_active=True,
                name__icontains='по умолчанию'
            ).first()
        except SalaryConfig.DoesNotExist:
            return None
    
    @staticmethod
    def calculate_installer_salary(
        installer: User, 
        start_date: datetime = None, 
        end_date: datetime = None
    ) -> Dict:
        """Расчет зарплаты монтажника с учетом настроек"""
        # Парсим и нормализуем даты
        start_date = _parse_date_param(start_date)
        end_date = _parse_date_param(end_date)
        
        if not start_date:
            today = timezone.now()
            start_date = timezone.make_aware(datetime(today.year, today.month, 1))
        if not end_date:
            end_date = timezone.now()
        
        # Получаем конфигурацию зарплаты
        config = SalaryCalculationService.get_user_salary_config(installer)
        if not config or not hasattr(config, 'installer_config'):
            # Возвращаем расчет по старой логике, если нет настроек
            return SalaryCalculationService._legacy_installer_calculation(
                installer, start_date, end_date
            )
        
        installer_config = config.installer_config
        
        # Завершенные заказы за период
        completed_orders = Order.objects.filter(
            installers=installer,
            status='completed',
            completed_at__gte=start_date,
            completed_at__lte=end_date
        )
        
        # Базовая оплата за монтажи
        installation_pay = installer_config.payment_per_installation * completed_orders.count()
        
        # Дополнительные услуги, проданные монтажником
        additional_services = OrderItem.objects.filter(
            order__in=completed_orders,
            service__category='additional',
            seller=installer
        )
        
        # Процент с прибыли от дополнительных услуг
        additional_pay = Decimal('0.00')
        for item in additional_services:
            profit = item.price - item.service.cost_price
            additional_pay += profit * (installer_config.additional_services_profit_percentage / 100)
        
        # Получаем корректировки за период
        adjustments = SalaryAdjustment.objects.filter(
            user=installer,
            period_start__lte=end_date,
            period_end__gte=start_date
        )
        
        total_adjustments = sum(adj.amount for adj in adjustments)
        
        # Общая зарплата
        total_salary = installation_pay + additional_pay + total_adjustments

        paid = SalaryPayment.objects.filter(
            user=installer,
            period_start__gte=start_date,
            period_end__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        remaining = total_salary - paid
        
        return {
            'config_name': config.name,
            'installation_pay': installation_pay,
            'installation_count': completed_orders.count(),
            'additional_pay': additional_pay,
            'additional_services_count': additional_services.count(),
            'adjustments': total_adjustments,
            'adjustments_details': [
                {
                    'type': adj.get_adjustment_type_display(),
                    'amount': adj.amount,
                    'reason': adj.reason
                } for adj in adjustments
            ],
            'total_salary': total_salary,
            'period': f"{start_date.date()} - {end_date.date()}",
            'paid': paid,
            'remaining': remaining,
        }
    
    @staticmethod
    def calculate_manager_salary(
        manager: User, 
        start_date: datetime = None, 
        end_date: datetime = None
    ) -> Dict:
        """Расчет зарплаты менеджера с учетом настроек"""
        # Парсим и нормализуем даты
        start_date = _parse_date_param(start_date)
        end_date = _parse_date_param(end_date)
        
        if not start_date:
            today = timezone.now()
            start_date = timezone.make_aware(datetime(today.year, today.month, 1))
        if not end_date:
            end_date = timezone.now()
        
        # Получаем конфигурацию зарплаты
        config = SalaryCalculationService.get_user_salary_config(manager)
        if not config or not hasattr(config, 'manager_config'):
            # Возвращаем расчет по старой логике, если нет настроек
            return SalaryCalculationService._legacy_manager_calculation(
                manager, start_date, end_date
            )
        
        manager_config = config.manager_config
        
        # Фиксированная зарплата
        fixed_salary = manager_config.fixed_salary
        
        # Завершенные заказы за период
        completed_orders = Order.objects.filter(
            manager=manager,
            status='completed',
            completed_at__gte=start_date,
            completed_at__lte=end_date
        )
        
        # Бонус за завершенные заказы
        orders_bonus = manager_config.bonus_per_completed_order * completed_orders.count()
        
        # Продажи по категориям
        sales_bonus = Decimal('0.00')
        sales_details = {}
        
        # Проходим по всем позициям заказов
        order_items = OrderItem.objects.filter(
            order__in=completed_orders,
            seller=manager
        ).select_related('service')
        
        for item in order_items:
            profit = item.price - item.service.cost_price
            category = item.service.category
            
            # Определяем процент в зависимости от категории
            percentage = Decimal('0.00')
            if category == 'conditioner':
                percentage = manager_config.conditioner_profit_percentage
            elif category == 'additional':
                percentage = manager_config.additional_services_profit_percentage
            elif category == 'installation':
                percentage = manager_config.installation_profit_percentage
            elif category == 'maintenance':
                percentage = manager_config.maintenance_profit_percentage
            elif category == 'dismantling':
                percentage = manager_config.dismantling_profit_percentage
            
            bonus = profit * (percentage / 100)
            sales_bonus += bonus
            
            # Сохраняем детали для отчета
            if category not in sales_details:
                sales_details[category] = {
                    'count': 0,
                    'profit': Decimal('0.00'),
                    'bonus': Decimal('0.00'),
                    'percentage': percentage
                }
            
            sales_details[category]['count'] += 1
            sales_details[category]['profit'] += profit
            sales_details[category]['bonus'] += bonus
        
        # Получаем корректировки за период
        adjustments = SalaryAdjustment.objects.filter(
            user=manager,
            period_start__lte=end_date,
            period_end__gte=start_date
        )
        
        total_adjustments = sum(adj.amount for adj in adjustments)
        
        # Общая зарплата
        total_salary = fixed_salary + orders_bonus + sales_bonus + total_adjustments

        paid = SalaryPayment.objects.filter(
            user=manager,
            period_start__gte=start_date,
            period_end__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        remaining = total_salary - paid
        
        return {
            'config_name': config.name,
            'fixed_salary': fixed_salary,
            'orders_bonus': orders_bonus,
            'completed_orders_count': completed_orders.count(),
            'sales_bonus': sales_bonus,
            'sales_details': sales_details,
            'adjustments': total_adjustments,
            'adjustments_details': [
                {
                    'type': adj.get_adjustment_type_display(),
                    'amount': adj.amount,
                    'reason': adj.reason
                } for adj in adjustments
            ],
            'total_salary': total_salary,
            'period': f"{start_date.date()} - {end_date.date()}",
            'paid': paid,
            'remaining': remaining,
        }
    
    @staticmethod
    def calculate_owner_salary(
        start_date: datetime = None, 
        end_date: datetime = None
    ) -> Dict:
        """Расчет зарплаты владельца с учетом настроек"""
        # Парсим и нормализуем даты
        start_date = _parse_date_param(start_date)
        end_date = _parse_date_param(end_date)
        
        if not start_date:
            today = timezone.now()
            start_date = timezone.make_aware(datetime(today.year, today.month, 1))
        if not end_date:
            end_date = timezone.now()
        
        # Получаем активную конфигурацию владельца
        try:
            config = SalaryConfig.objects.filter(
                is_active=True,
                owner_config__isnull=False
            ).first()
        except SalaryConfig.DoesNotExist:
            config = None
        
        if not config or not hasattr(config, 'owner_config'):
            # Возвращаем расчет по старой логике, если нет настроек
            return SalaryCalculationService._legacy_owner_calculation(start_date, end_date)
        
        owner_config = config.owner_config
        
        # Все завершенные заказы за период
        completed_orders = Order.objects.filter(
            status='completed',
            completed_at__gte=start_date,
            completed_at__lte=end_date
        )
        
        # Доля с каждого монтажа
        installation_pay = owner_config.payment_per_installation * completed_orders.count()
        
        # Общая выручка
        total_revenue = OrderItem.objects.filter(
            order__in=completed_orders
        ).aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
        
        # Общая себестоимость
        total_cost_price = sum(
            item.service.cost_price
            for item in OrderItem.objects.filter(order__in=completed_orders)
        )
        
        # Валовая прибыль
        gross_profit = total_revenue - total_cost_price
        
        # Расчет выплат сотрудникам (упрощенный)
        # В реальности нужно рассчитывать по их конфигурациям
        estimated_staff_payments = SalaryCalculationService._estimate_staff_payments(
            completed_orders, start_date, end_date
        )
        
        # Оставшаяся прибыль
        remaining_profit = gross_profit - estimated_staff_payments - installation_pay
        
        # Доля владельца от оставшейся прибыли
        owner_profit_share = remaining_profit * (owner_config.remaining_profit_percentage / 100)
        
        # Получаем корректировки для владельца
        owner_user = User.objects.filter(role='owner').first()
        adjustments = Decimal('0.00')
        adjustments_details = []
        
        if owner_user:
            owner_adjustments = SalaryAdjustment.objects.filter(
                user=owner_user,
                period_start__lte=end_date,
                period_end__gte=start_date
            )
            adjustments = sum(adj.amount for adj in owner_adjustments)
            adjustments_details = [
                {
                    'type': adj.get_adjustment_type_display(),
                    'amount': adj.amount,
                    'reason': adj.reason
                } for adj in owner_adjustments
            ]
        
        # Общая зарплата владельца
        total_salary = installation_pay + owner_profit_share + adjustments

        paid = SalaryPayment.objects.filter(
            user=owner_user,
            period_start__gte=start_date,
            period_end__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        remaining = total_salary - paid
        
        return {
            'config_name': config.name,
            'installation_pay': installation_pay,
            'completed_orders_count': completed_orders.count(),
            'total_revenue': total_revenue,
            'total_cost_price': total_cost_price,
            'gross_profit': gross_profit,
            'estimated_staff_payments': estimated_staff_payments,
            'remaining_profit': remaining_profit,
            'owner_profit_share': owner_profit_share,
            'adjustments': adjustments,
            'adjustments_details': adjustments_details,
            'total_salary': total_salary,
            'period': f"{start_date.date()} - {end_date.date()}",
            'paid': paid,
            'remaining': remaining,
        }
    
    @staticmethod
    def _estimate_staff_payments(completed_orders, start_date, end_date) -> Decimal:
        """Приблизительный расчет выплат сотрудникам"""
        # Это упрощенный расчет для владельца
        # В реальности нужно суммировать фактические расчеты по всем сотрудникам
        
        orders_count = completed_orders.count()
        
        # Примерная оценка выплат монтажникам (1500 за монтаж * среднее количество монтажников)
        estimated_installer_payments = orders_count * Decimal('1500.00') * 2
        
        # Примерная оценка выплат менеджерам (фикс + бонусы)
        managers_count = User.objects.filter(role='manager').count()
        estimated_manager_payments = managers_count * Decimal('30000.00')  # Фиксированная часть
        estimated_manager_payments += orders_count * Decimal('250.00')  # Бонусы за заказы
        
        return estimated_installer_payments + estimated_manager_payments
    
    @staticmethod
    def _legacy_installer_calculation(installer, start_date, end_date) -> Dict:
        """Старая логика расчета для совместимости"""
        completed_orders = Order.objects.filter(
            installers=installer,
            status='completed',
            completed_at__gte=start_date,
            completed_at__lte=end_date
        )
        
        installation_pay = Decimal('1500.00') * completed_orders.count()
        
        additional_services = OrderItem.objects.filter(
            order__in=completed_orders,
            service__category='additional',
            seller=installer
        )
        
        additional_pay = sum(
            (item.price - item.service.cost_price) * Decimal('0.3')
            for item in additional_services
        )
        
        return {
            'config_name': 'Стандартная (legacy)',
            'installation_pay': installation_pay,
            'installation_count': completed_orders.count(),
            'additional_pay': additional_pay,
            'additional_services_count': additional_services.count(),
            'adjustments': Decimal('0.00'),
            'adjustments_details': [],
            'total_salary': installation_pay + additional_pay,
            'period': f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"
        }
    
    @staticmethod
    def _legacy_manager_calculation(manager, start_date, end_date) -> Dict:
        """Старая логика расчета для совместимости"""
        fixed_salary = Decimal('30000.00')
        
        completed_orders = Order.objects.filter(
            manager=manager,
            status='completed',
            completed_at__gte=start_date,
            completed_at__lte=end_date
        )
        
        orders_bonus = Decimal('250.00') * completed_orders.count()
        
        # Старая логика бонусов
        conditioner_sales = OrderItem.objects.filter(
            order__in=completed_orders,
            service__category='conditioner',
            seller=manager
        )
        
        conditioner_bonus = sum(
            (item.price - item.service.cost_price) * Decimal('0.2')
            for item in conditioner_sales
        )
        
        additional_sales = OrderItem.objects.filter(
            order__in=completed_orders,
            service__category='additional',
            seller=manager
        )
        
        additional_bonus = sum(
            (item.price - item.service.cost_price) * Decimal('0.3')
            for item in additional_sales
        )
        
        total_salary = fixed_salary + orders_bonus + conditioner_bonus + additional_bonus
        
        return {
            'config_name': 'Стандартная (legacy)',
            'fixed_salary': fixed_salary,
            'orders_bonus': orders_bonus,
            'completed_orders_count': completed_orders.count(),
            'sales_bonus': conditioner_bonus + additional_bonus,
            'sales_details': {
                'conditioner': {
                    'count': conditioner_sales.count(),
                    'bonus': conditioner_bonus,
                    'percentage': Decimal('20.00')
                },
                'additional': {
                    'count': additional_sales.count(), 
                    'bonus': additional_bonus,
                    'percentage': Decimal('30.00')
                }
            },
            'adjustments': Decimal('0.00'),
            'adjustments_details': [],
            'total_salary': total_salary,
            'period': f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"
        }
    
    @staticmethod
    def _legacy_owner_calculation(start_date, end_date) -> Dict:
        """Старая логика расчета для совместимости"""
        completed_orders = Order.objects.filter(
            status='completed',
            completed_at__gte=start_date,
            completed_at__lte=end_date
        )
        
        installation_pay = Decimal('1500.00') * completed_orders.count()
        
        total_revenue = OrderItem.objects.filter(
            order__in=completed_orders
        ).aggregate(Sum('price'))['price__sum'] or Decimal('0.00')
        
        total_cost_price = sum(
            item.service.cost_price
            for item in OrderItem.objects.filter(order__in=completed_orders)
        )
        
        # Упрощенный расчет выплат сотрудникам
        installers_pay = Decimal('1500.00') * completed_orders.count() * Decimal('2')
        managers_pay = Decimal('30000.00') + (Decimal('250.00') * completed_orders.count())
        
        remaining_profit = total_revenue - total_cost_price - installers_pay - managers_pay
        total_salary = installation_pay + remaining_profit
        
        return {
            'config_name': 'Стандартная (legacy)',
            'installation_pay': installation_pay,
            'completed_orders_count': completed_orders.count(),
            'total_revenue': total_revenue,
            'total_cost_price': total_cost_price,
            'gross_profit': total_revenue - total_cost_price,
            'estimated_staff_payments': installers_pay + managers_pay,
            'remaining_profit': remaining_profit,
            'owner_profit_share': remaining_profit,
            'adjustments': Decimal('0.00'),
            'adjustments_details': [],
            'total_salary': total_salary,
            'period': f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"
        }


class SalaryConfigService:
    """Сервис для управления конфигурациями зарплат"""
    
    @staticmethod
    def create_default_config() -> SalaryConfig:
        """Создает конфигурацию по умолчанию"""
        config = SalaryConfig.objects.create(
            name="Стандартная конфигурация",
            description="Конфигурация зарплат по умолчанию",
            is_active=True
        )
        
        # Создаем настройки для менеджеров
        ManagerSalaryConfig.objects.create(
            config=config,
            fixed_salary=Decimal('30000.00'),
            bonus_per_completed_order=Decimal('250.00'),
            conditioner_profit_percentage=Decimal('20.00'),
            additional_services_profit_percentage=Decimal('30.00'),
            installation_profit_percentage=Decimal('15.00'),
            maintenance_profit_percentage=Decimal('25.00'),
            dismantling_profit_percentage=Decimal('20.00')
        )
        
        # Создаем настройки для монтажников
        InstallerSalaryConfig.objects.create(
            config=config,
            payment_per_installation=Decimal('1500.00'),
            additional_services_profit_percentage=Decimal('30.00'),
            quality_bonus=Decimal('0.00'),
            penalty_per_complaint=Decimal('500.00')
        )
        
        # Создаем настройки для владельца
        OwnerSalaryConfig.objects.create(
            config=config,
            payment_per_installation=Decimal('1500.00'),
            remaining_profit_percentage=Decimal('100.00')
        )
        
        return config
    
    @staticmethod
    def assign_config_to_user(user: User, config: SalaryConfig):
        """Назначает конфигурацию пользователю"""
        UserSalaryAssignment.objects.update_or_create(
            user=user,
            defaults={'config': config}
        )
    
    @staticmethod
    def get_users_without_config():
        """Возвращает пользователей без назначенной конфигурации зарплаты"""
        return User.objects.exclude(
            id__in=UserSalaryAssignment.objects.values_list('user_id', flat=True)
        ).filter(role__in=['manager', 'installer', 'owner'])
    
    @staticmethod
    def bulk_assign_default_config():
        """Массово назначает конфигурацию по умолчанию всем пользователям без настроек"""
        default_config = SalaryConfig.objects.filter(
            is_active=True,
            name__icontains='умолчанию'
        ).first()
        
        if not default_config:
            default_config = SalaryConfigService.create_default_config()
        
        users_without_config = SalaryConfigService.get_users_without_config()
        
        assignments = []
        for user in users_without_config:
            assignments.append(
                UserSalaryAssignment(user=user, config=default_config)
            )
        
        UserSalaryAssignment.objects.bulk_create(assignments)
        return len(assignments)
