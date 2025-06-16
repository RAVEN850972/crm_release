from django.db import models

class Service(models.Model):
    CATEGORY_CHOICES = (
        ('conditioner', 'Кондиционер'),
        ('installation', 'Монтаж'),
        ('dismantling', 'Демонтаж'),
        ('maintenance', 'Обслуживание'),
        ('additional', 'Доп услуга'),
    )
    
    name = models.CharField(max_length=100, verbose_name="Название")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Себестоимость")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена продажи")
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, verbose_name="Категория")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
    
    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"