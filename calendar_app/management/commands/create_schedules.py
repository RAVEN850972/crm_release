# calendar_app/management/commands/create_schedules.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta, time
from django.conf import settings
from calendar_app.services import CalendarService
from calendar_app.models import InstallationSchedule
from orders.models import Order
from user_accounts.models import User

class Command(BaseCommand):
    help = 'Автоматическое создание расписаний для заказов без расписания'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            type=str,
            help='Начальная дата для планирования (YYYY-MM-DD). По умолчанию - завтра'
        )
        parser.add_argument(
            '--auto-assign',
            action='store_true',
            help='Автоматически назначать доступных монтажников'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать план без создания расписаний'
        )

    def handle(self, *args, **options):
        # Определяем начальную дату
        if options['start_date']:
            try:
                start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Неверный формат даты. Используйте YYYY-MM-DD')
                )
                return
        else:
            start_date = timezone.now().date() + timedelta(days=1)  # Завтра

        # Получаем настройки календаря
        calendar_settings = getattr(settings, 'CALENDAR_SETTINGS', {})
        work_start = calendar_settings.get('DEFAULT_WORK_START_TIME', '08:00')
        work_end = calendar_settings.get('DEFAULT_WORK_END_TIME', '18:00')
        default_duration = calendar_settings.get('DEFAULT_INSTALLATION_DURATION', 2)
        max_per_day = calendar_settings.get('MAX_INSTALLATIONS_PER_DAY', 5)

        work_start_time = datetime.strptime(work_start, '%H:%M').time()
        work_end_time = datetime.strptime(work_end, '%H:%M').time()

        # Находим заказы без расписания
        orders_without_schedule = Order.objects.filter(
            status__in=['new', 'in_progress'],
            schedule__isnull=True
        ).select_related('client', 'manager').prefetch_related('installers')

        if not orders_without_schedule:
            self.stdout.write(
                self.style.SUCCESS('Все заказы уже имеют расписания')
            )
            return

        self.stdout.write(
            f'Найдено {orders_without_schedule.count()} заказов без расписания'
        )

        # Получаем доступных монтажников
        available_installers = User.objects.filter(role='installer', is_active=True)
        
        if not available_installers:
            self.stdout.write(
                self.style.ERROR('Нет доступных монтажников')
            )
            return

        # Планируем расписания
        current_date = start_date
        schedules_created = 0
        
        for order in orders_without_schedule:
            self.stdout.write(f'\nПланирование заказа #{order.id} - {order.client.name}')
            
            # Определяем приоритет на основе даты создания заказа
            days_old = (timezone.now().date() - order.created_at.date()).days
            if days_old > 7:
                priority = 'high'
            elif days_old > 3:
                priority = 'normal'
            else:
                priority = 'low'

            # Определяем продолжительность на основе количества услуг
            services_count = order.items.count()
            if services_count <= 1:
                duration_hours = 1
            elif services_count <= 3:
                duration_hours = 2
            else:
                duration_hours = 3

            # Ищем подходящее время
            scheduled = False
            search_date = current_date
            max_search_days = 14  # Максимум 2 недели вперед

            for day_offset in range(max_search_days):
                search_date = current_date + timedelta(days=day_offset)
                
                # Проверяем выходные (можно настроить)
                if search_date.weekday() >= 5:  # Суббота и воскресенье
                    continue

                # Ищем доступных монтажников на этот день
                for installer in available_installers:
                    # Проверяем загруженность монтажника
                    daily_schedules = InstallationSchedule.objects.filter(
                        installers=installer,
                        scheduled_date=search_date,
                        status__in=['scheduled', 'in_progress']
                    ).count()

                    if daily_schedules >= max_per_day:
                        continue

                    # Ищем свободное время
                    existing_schedules = InstallationSchedule.objects.filter(
                        installers=installer,
                        scheduled_date=search_date,
                        status__in=['scheduled', 'in_progress']
                    ).order_by('scheduled_time_start')

                    # Простой алгоритм поиска свободного слота
                    current_time = work_start_time
                    slot_found = False

                    for existing_schedule in existing_schedules:
                        # Проверяем, помещается ли наше время до следующего расписания
                        end_time = datetime.combine(search_date, current_time)
                        end_time += timedelta(hours=duration_hours)
                        
                        if end_time.time() <= existing_schedule.scheduled_time_start:
                            slot_found = True
                            break
                        
                        # Сдвигаем время после этого расписания
                        current_time = existing_schedule.scheduled_time_end

                    # Если не нашли слот между расписаниями, проверяем после последнего
                    if not slot_found:
                        end_time = datetime.combine(search_date, current_time)
                        end_time += timedelta(hours=duration_hours)
                        
                        if end_time.time() <= work_end_time:
                            slot_found = True

                    if slot_found:
                        # Создаем расписание
                        end_time = datetime.combine(search_date, current_time)
                        end_time += timedelta(hours=duration_hours)

                        schedule_data = {
                            'scheduled_date': search_date,
                            'start_time': current_time,
                            'end_time': end_time.time(),
                            'installers_ids': [installer.id],
                            'priority': priority,
                            'estimated_duration': timedelta(hours=duration_hours),
                            'notes': f'Автоматически запланировано ({services_count} услуг)'
                        }

                        if options['dry_run']:
                            self.stdout.write(
                                f'  План: {search_date} {current_time}-{end_time.time()} '
                                f'({installer.get_full_name()}, приоритет: {priority})'
                            )
                        else:
                            try:
                                CalendarService.create_schedule(
                                    order=order,
                                    **schedule_data
                                )
                                schedules_created += 1
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'  ✓ Запланировано: {search_date} {current_time}-{end_time.time()} '
                                        f'({installer.get_full_name()})'
                                    )
                                )
                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(f'  Ошибка создания расписания: {str(e)}')
                                )

                        scheduled = True
                        break

                if scheduled:
                    break

            if not scheduled:
                self.stdout.write(
                    self.style.WARNING(f'  Не удалось запланировать заказ #{order.id} в ближайшие {max_search_days} дней')
                )

        # Итоговая статистика
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(f'\nПлан создания {schedules_created} расписаний готов')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nСоздано {schedules_created} расписаний')
            )

            # Предлагаем оптимизировать маршруты
            if schedules_created > 0:
                self.stdout.write('\nРекомендуется запустить оптимизацию маршрутов:')
                self.stdout.write('python manage.py optimize_routes --days-ahead 7')