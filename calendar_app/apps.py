# calendar_app/apps.py
from django.apps import AppConfig

class CalendarAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'calendar_app'
    verbose_name = 'Календарь монтажей'
    
    def ready(self):
        # Импортируем сигналы, если они понадобятся
        pass