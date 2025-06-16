# salary_config/apps.py
from django.apps import AppConfig

class SalaryConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'salary_config'
    verbose_name = 'Настройки зарплат'
    
    def ready(self):
        # Импортируем сигналы, если понадобятся
        pass