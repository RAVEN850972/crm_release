# salary_config/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from user_accounts.models import User

class SalaryConfig(models.Model):
    """Базовая конфигурация зарплат"""
    name = models.CharField(max_length=100, verbose_name="Название конфигурации")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Конфигурация зарплат"
        verbose_name_plural = "Конфигурации зарплат"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class ManagerSalaryConfig(models.Model):
    """Настройки зарплаты для менеджеров"""
    config = models.OneToOneField(
        SalaryConfig, 
        on_delete=models.CASCADE, 
        related_name='manager_config',
        verbose_name="Конфигурация"
    )
    
    # Фиксированная часть
    fixed_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('30000.00'),
        verbose_name="Фиксированная зарплата",
        help_text="Оклад в рублях"
    )
    
    # Бонусы за заказы
    bonus_per_completed_order = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('250.00'),
        verbose_name="Бонус за завершенный заказ",
        help_text="Сумма в рублях за каждый завершенный заказ"
    )
    
    # Проценты с продаж кондиционеров
    conditioner_profit_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('20.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="% с прибыли от кондиционеров",
        help_text="Процент от прибыли с продажи кондиционеров"
    )
    
    # Проценты с продаж дополнительных услуг
    additional_services_profit_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('30.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="% с прибыли от доп. услуг",
        help_text="Процент от прибыли с продажи дополнительных услуг"
    )
    
    # Проценты с других категорий услуг
    installation_profit_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('15.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="% с прибыли от монтажа",
        help_text="Процент от прибыли с услуг монтажа"
    )
    
    maintenance_profit_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('25.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="% с прибыли от обслуживания",
        help_text="Процент от прибыли с услуг обслуживания"
    )
    
    dismantling_profit_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('20.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="% с прибыли от демонтажа",
        help_text="Процент от прибыли с услуг демонтажа"
    )
    
    class Meta:
        verbose_name = "Настройки зарплаты менеджера"
        verbose_name_plural = "Настройки зарплат менеджеров"
    
    def __str__(self):
        return f"Менеджер - {self.config.name}"

class InstallerSalaryConfig(models.Model):
    """Настройки зарплаты для монтажников"""
    config = models.OneToOneField(
        SalaryConfig, 
        on_delete=models.CASCADE, 
        related_name='installer_config',
        verbose_name="Конфигурация"
    )
    
    # Оплата за монтаж
    payment_per_installation = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('1500.00'),
        verbose_name="Оплата за монтаж",
        help_text="Фиксированная сумма за каждый завершенный монтаж"
    )
    
    # Проценты с дополнительных услуг (которые продал монтажник)
    additional_services_profit_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('30.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="% с прибыли от доп. услуг",
        help_text="Процент от прибыли с дополнительных услуг, проданных монтажником"
    )
    
    # Штрафы и бонусы
    quality_bonus = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Бонус за качество",
        help_text="Дополнительный бонус за качественную работу"
    )
    
    penalty_per_complaint = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('500.00'),
        verbose_name="Штраф за жалобу",
        help_text="Штраф за обоснованную жалобу клиента"
    )
    
    class Meta:
        verbose_name = "Настройки зарплаты монтажника"
        verbose_name_plural = "Настройки зарплат монтажников"
    
    def __str__(self):
        return f"Монтажник - {self.config.name}"

class OwnerSalaryConfig(models.Model):
    """Настройки зарплаты для владельца"""
    config = models.OneToOneField(
        SalaryConfig, 
        on_delete=models.CASCADE, 
        related_name='owner_config',
        verbose_name="Конфигурация"
    )
    
    # Фиксированная часть за монтажи
    payment_per_installation = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=Decimal('1500.00'),
        verbose_name="Доля с каждого монтажа",
        help_text="Фиксированная сумма с каждого завершенного монтажа"
    )
    
    # Процент от оставшейся прибыли
    remaining_profit_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('100.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="% от оставшейся прибыли",
        help_text="Процент от прибыли после выплат менеджерам и монтажникам"
    )
    
    class Meta:
        verbose_name = "Настройки зарплаты владельца"
        verbose_name_plural = "Настройки зарплат владельцев"
    
    def __str__(self):
        return f"Владелец - {self.config.name}"

class UserSalaryAssignment(models.Model):
    """Назначение конкретной конфигурации зарплаты пользователю"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='salary_assignment',
        verbose_name="Пользователь"
    )
    config = models.ForeignKey(
        SalaryConfig, 
        on_delete=models.CASCADE,
        verbose_name="Конфигурация зарплаты"
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата назначения")
    
    class Meta:
        verbose_name = "Назначение зарплаты"
        verbose_name_plural = "Назначения зарплат"
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.config.name}"

class SalaryAdjustment(models.Model):
    """Корректировки зарплаты (премии, штрафы)"""
    ADJUSTMENT_TYPES = (
        ('bonus', 'Премия'),
        ('penalty', 'Штраф'),
        ('correction', 'Корректировка'),
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='salary_adjustments',
        verbose_name="Сотрудник"
    )
    adjustment_type = models.CharField(
        max_length=20, 
        choices=ADJUSTMENT_TYPES,
        verbose_name="Тип корректировки"
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Сумма",
        help_text="Положительная для премий, отрицательная для штрафов"
    )
    reason = models.TextField(verbose_name="Причина")
    period_start = models.DateField(verbose_name="Начало периода")
    period_end = models.DateField(verbose_name="Конец периода")
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='created_adjustments',
        verbose_name="Создано пользователем"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    class Meta:
        verbose_name = "Корректировка зарплаты"
        verbose_name_plural = "Корректировки зарплат"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_adjustment_type_display()} {self.amount} для {self.user.get_full_name()}"