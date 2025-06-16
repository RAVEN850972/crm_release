# calendar_app/migrations/0001_initial.py
# Generated manually for calendar_app

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('orders', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InstallationSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheduled_date', models.DateField(verbose_name='Дата монтажа')),
                ('scheduled_time_start', models.TimeField(verbose_name='Время начала')),
                ('scheduled_time_end', models.TimeField(verbose_name='Время окончания')),
                ('status', models.CharField(choices=[('scheduled', 'Запланировано'), ('in_progress', 'Выполняется'), ('completed', 'Завершено'), ('cancelled', 'Отменено'), ('rescheduled', 'Перенесено')], default='scheduled', max_length=15, verbose_name='Статус')),
                ('priority', models.CharField(choices=[('low', 'Низкий'), ('normal', 'Обычный'), ('high', 'Высокий'), ('urgent', 'Срочно')], default='normal', max_length=10, verbose_name='Приоритет')),
                ('estimated_duration', models.DurationField(help_text='В формате HH:MM:SS', verbose_name='Ожидаемая продолжительность')),
                ('actual_start_time', models.DateTimeField(blank=True, null=True, verbose_name='Фактическое время начала')),
                ('actual_end_time', models.DateTimeField(blank=True, null=True, verbose_name='Фактическое время окончания')),
                ('notes', models.TextField(blank=True, help_text='Особые требования, комментарии', verbose_name='Заметки')),
                ('travel_time_to', models.DurationField(blank=True, null=True, verbose_name='Время в пути до объекта')),
                ('travel_distance_to', models.FloatField(blank=True, null=True, verbose_name='Расстояние до объекта (км)')),
                ('latitude', models.FloatField(blank=True, null=True, verbose_name='Широта')),
                ('longitude', models.FloatField(blank=True, null=True, verbose_name='Долгота')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('installers', models.ManyToManyField(limit_choices_to={'role': 'installer'}, to=settings.AUTH_USER_MODEL, verbose_name='Монтажники')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='schedule', to='orders.order', verbose_name='Заказ')),
            ],
            options={
                'verbose_name': 'Расписание монтажа',
                'verbose_name_plural': 'Расписания монтажей',
                'ordering': ['scheduled_date', 'scheduled_time_start'],
            },
        ),
        migrations.CreateModel(
            name='RouteOptimization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='Дата')),
                ('total_distance', models.FloatField(blank=True, null=True, verbose_name='Общее расстояние (км)')),
                ('total_travel_time', models.DurationField(blank=True, null=True, verbose_name='Общее время в пути')),
                ('start_location', models.CharField(blank=True, help_text='Адрес склада или дома монтажника', max_length=200, verbose_name='Начальная точка')),
                ('is_optimized', models.BooleanField(default=False, verbose_name='Маршрут оптимизирован')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('installer', models.ForeignKey(limit_choices_to={'role': 'installer'}, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Монтажник')),
            ],
            options={
                'verbose_name': 'Оптимизация маршрута',
                'verbose_name_plural': 'Оптимизации маршрутов',
            },
        ),
        migrations.CreateModel(
            name='RoutePoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence_number', models.PositiveIntegerField(verbose_name='Порядковый номер')),
                ('arrival_time', models.TimeField(blank=True, null=True, verbose_name='Время прибытия')),
                ('departure_time', models.TimeField(blank=True, null=True, verbose_name='Время отъезда')),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='calendar_app.routeoptimization')),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='calendar_app.installationschedule')),
            ],
            options={
                'verbose_name': 'Точка маршрута',
                'verbose_name_plural': 'Точки маршрута',
                'ordering': ['sequence_number'],
            },
        ),
        migrations.AddField(
            model_name='routeoptimization',
            name='schedules',
            field=models.ManyToManyField(through='calendar_app.RoutePoint', to='calendar_app.installationschedule', verbose_name='Монтажи в маршруте'),
        ),
        migrations.AlterUniqueTogether(
            name='routepoint',
            unique_together={('route', 'sequence_number')},
        ),
        migrations.AlterUniqueTogether(
            name='routeoptimization',
            unique_together={('date', 'installer')},
        ),
    ]