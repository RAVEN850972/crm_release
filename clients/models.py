from django.db import models

class Client(models.Model):
    SOURCE_CHOICES = (
        ('avito', 'Авито'),
        ('vk', 'ВК'),
        ('website', 'Сайт'),
        ('recommendations', 'Рекомендации'),
        ('other', 'Другое'),
    )
    
    name = models.CharField(max_length=100, verbose_name="Имя")
    address = models.CharField(max_length=200, verbose_name="Адрес")
    phone = models.CharField(max_length=15, verbose_name="Телефон")
    source = models.CharField(max_length=15, choices=SOURCE_CHOICES, verbose_name="Источник")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    def __str__(self):
        return f"{self.name} ({self.phone})"
    
    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"