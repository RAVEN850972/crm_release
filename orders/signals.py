# orders/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Order
from finance.models import Transaction

@receiver(pre_save, sender=Order)
def track_order_status_change(sender, instance, **kwargs):
    """Отслеживаем изменение статуса заказа"""
    if instance.pk:  # Если заказ уже существует
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Order)
def create_transaction_on_completion(sender, instance, created, **kwargs):
    """Создаем транзакцию при завершении заказа"""
    if not created:  # Только для обновленных заказов
        old_status = getattr(instance, '_old_status', None)
        
        # Если статус изменился на 'completed' и заказ имеет позиции
        if (old_status != 'completed' and 
            instance.status == 'completed' and 
            instance.total_cost > 0):
            
            # Проверяем, что транзакция еще не создана для этого заказа
            existing_transaction = Transaction.objects.filter(
                order=instance,
                type='income'
            ).first()
            
            if not existing_transaction:
                # Создаем доходную транзакцию
                Transaction.objects.create(
                    type='income',
                    amount=instance.total_cost,
                    description=f'Доход от завершения заказа #{instance.id} - {instance.client.name}',
                    order=instance
                )
                
                # Обновляем дату завершения, если она не была установлена
                if not instance.completed_at:
                    instance.completed_at = timezone.now()
                    instance.save(update_fields=['completed_at'])

@receiver(post_save, sender=Order)
def create_expense_transactions_on_completion(sender, instance, created, **kwargs):
    """Создаем расходные транзакции при завершении заказа"""
    if not created:  # Только для обновленных заказов
        old_status = getattr(instance, '_old_status', None)
        
        # Если статус изменился на 'completed'
        if old_status != 'completed' and instance.status == 'completed':
            
            # Проверяем, что расходные транзакции еще не созданы
            existing_expenses = Transaction.objects.filter(
                order=instance,
                type='expense',
                description__contains='Себестоимость'
            ).exists()
            
            if not existing_expenses and instance.items.exists():
                # Рассчитываем общую себестоимость
                total_cost_price = sum(
                    item.service.cost_price for item in instance.items.all()
                )
                
                if total_cost_price > 0:
                    # Создаем расходную транзакцию на себестоимость
                    Transaction.objects.create(
                        type='expense',
                        amount=total_cost_price,
                        description=f'Себестоимость заказа #{instance.id} - {instance.client.name}',
                        order=instance
                    )