from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from user_accounts.models import User  # Исправлено с accounts.models
from customer_clients.models import Client  # Исправлено с clients.models
from services.models import Service

class Order(models.Model):
    STATUS_CHOICES = (
        ('new', 'Новый'),
        ('in_progress', 'В работе'),
        ('completed', 'Завершен'),
    )
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Клиент")
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name="managed_orders", verbose_name="Менеджер")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    installers = models.ManyToManyField(User, related_name="installation_orders", verbose_name="Монтажники", limit_choices_to={'role': 'installer'})
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Общая стоимость")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")
    
    def __str__(self):
        return f"Заказ #{self.id} - {self.client.name}"
    
    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Заказ")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name="Услуга")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    seller = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Продавец")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    def __str__(self):
        return f"{self.service.name} - {self.price}"
    
    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

@receiver(post_save, sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    order = instance.order
    total = sum(item.price for item in order.items.all())
    order.total_cost = total
    order.save()

