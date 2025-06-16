# calendar_app/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from user_accounts.models import User
from orders.models import Order

class InstallationSchedule(models.Model):
    """Расписание монтажей"""
    STATUS_CHOICES = (
        ('scheduled', 'Запланировано'),
        ('in_progress', 'Выполняется'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
        ('rescheduled', 'Перенесено'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Низкий'),
        ('normal', 'Обычный'),
        ('high', 'Высокий'),
        ('urgent', 'Срочно'),
    )
    
    order = models.OneToOneField(
        Order, 
        on_delete=models.CASCADE, 
        verbose_name="Заказ",
        related_name='schedule'
    )
    
    scheduled_date = models.DateField(verbose_name="Дата монтажа")
    scheduled_time_start = models.TimeField(verbose_name="Время начала")
    scheduled_time_end = models.TimeField(verbose_name="Время окончания")
    
    installers = models.ManyToManyField(
        User, 
        limit_choices_to={'role': 'installer'},
        verbose_name="Монтажники"
    )
    
    status = models.CharField(
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='scheduled',
        verbose_name="Статус"
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name="Приоритет"
    )
    
    estimated_duration = models.DurationField(
        verbose_name="Ожидаемая продолжительность",
        help_text="В формате HH:MM:SS"
    )
    
    actual_start_time = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Фактическое время начала"
    )
    
    actual_end_time = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Фактическое время окончания"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="Заметки",
        help_text="Особые требования, комментарии"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    # Поля для маршрутизации
    travel_time_to = models.DurationField(
        null=True, blank=True,
        verbose_name="Время в пути до объекта"
    )
    
    travel_distance_to = models.FloatField(
        null=True, blank=True,
        verbose_name="Расстояние до объекта (км)"
    )
    
    # Координаты для маршрутизации
    latitude = models.FloatField(null=True, blank=True, verbose_name="Широта")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Долгота")
    
    class Meta:
        verbose_name = "Расписание монтажа"
        verbose_name_plural = "Расписания монтажей"
        ordering = ['scheduled_date', 'scheduled_time_start']
        
    def __str__(self):
        return f"Монтаж #{self.order.id} - {self.scheduled_date} {self.scheduled_time_start}"
    
    def clean(self):
        """Валидация данных"""
        if self.scheduled_time_start and self.scheduled_time_end:
            if self.scheduled_time_start >= self.scheduled_time_end:
                raise ValidationError('Время начала должно быть раньше времени окончания')
        
        if self.actual_start_time and self.actual_end_time:
            if self.actual_start_time >= self.actual_end_time:
                raise ValidationError('Фактическое время начала должно быть раньше времени окончания')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    @property
    def duration(self):
        """Фактическая продолжительность"""
        if self.actual_start_time and self.actual_end_time:
            return self.actual_end_time - self.actual_start_time
        return None
    
    @property
    def is_overdue(self):
        """Проверка просрочки"""
        if self.status in ['completed', 'cancelled']:
            return False
        
        from datetime import datetime, time
        scheduled_datetime = datetime.combine(self.scheduled_date, self.scheduled_time_end)
        return timezone.now() > timezone.make_aware(scheduled_datetime)

class RouteOptimization(models.Model):
    """Оптимизация маршрутов для монтажников"""
    date = models.DateField(verbose_name="Дата")
    installer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'installer'},
        verbose_name="Монтажник"
    )
    
    schedules = models.ManyToManyField(
        InstallationSchedule,
        through='RoutePoint',
        verbose_name="Монтажи в маршруте"
    )
    
    total_distance = models.FloatField(
        null=True, blank=True,
        verbose_name="Общее расстояние (км)"
    )
    
    total_travel_time = models.DurationField(
        null=True, blank=True,
        verbose_name="Общее время в пути"
    )
    
    start_location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Начальная точка",
        help_text="Адрес склада или дома монтажника"
    )
    
    is_optimized = models.BooleanField(
        default=False,
        verbose_name="Маршрут оптимизирован"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Оптимизация маршрута"
        verbose_name_plural = "Оптимизации маршрутов"
        unique_together = ('date', 'installer')
        
    def __str__(self):
        return f"Маршрут {self.installer.get_full_name()} - {self.date}"

class RoutePoint(models.Model):
    """Точка в маршруте"""
    route = models.ForeignKey(RouteOptimization, on_delete=models.CASCADE)
    schedule = models.ForeignKey(InstallationSchedule, on_delete=models.CASCADE)
    sequence_number = models.PositiveIntegerField(verbose_name="Порядковый номер")
    
    # Данные для оптимизации
    arrival_time = models.TimeField(null=True, blank=True, verbose_name="Время прибытия")
    departure_time = models.TimeField(null=True, blank=True, verbose_name="Время отъезда")
    
    class Meta:
        verbose_name = "Точка маршрута"
        verbose_name_plural = "Точки маршрута"
        ordering = ['sequence_number']
        unique_together = ('route', 'sequence_number')
        
    def __str__(self):
        return f"Точка {self.sequence_number} - {self.schedule}"