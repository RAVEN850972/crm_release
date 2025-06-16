from django.db import models
from django.db.models import Sum
from user_accounts.models import User  # Исправлено с accounts.models
from orders.models import Order

class Transaction(models.Model):
    TYPE_CHOICES = (
        ('income', 'Доход'),
        ('expense', 'Расход'),
    )
    
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Тип")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    description = models.TextField(verbose_name="Описание")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Связанный заказ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.amount}"
    
    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        
    @classmethod
    def get_company_balance(cls):
        income = cls.objects.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
        expense = cls.objects.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
        return income - expense

class SalaryPayment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Сотрудник")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    period_start = models.DateField(verbose_name="Начало периода")
    period_end = models.DateField(verbose_name="Конец периода")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    def __str__(self):
        return f"ЗП для {self.user.get_full_name()} - {self.amount}"
    
    class Meta:
        verbose_name = "Выплата зарплаты"
        verbose_name_plural = "Выплаты зарплат"