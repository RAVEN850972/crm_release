# calendar_app/management/commands/optimize_routes.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from calendar_app.services import RouteOptimizationService
from calendar_app.models import InstallationSchedule
from user_accounts.models import User

class Command(BaseCommand):
    help = 'Автоматическая оптимизация маршрутов для всех монтажников'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Дата для оптимизации (YYYY-MM-DD). По умолчанию - завтра'
        )
        parser.add_argument(
            '--installer',
            type=int,
            help='ID конкретного монтажника для оптимизации'
        )
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=1,
            help='Количество дней вперед для оптимизации (по умолчанию 1)'
        )

    def handle(self, *args, **options):
        # Определяем дату для оптимизации
        if options['date']:
            try:
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Неверный формат даты. Используйте YYYY-MM-DD')
                )
                return
        else:
            target_date = timezone.now().date() + timedelta(days=1)  # Завтра

        # Определяем монтажников
        if options['installer']:
            try:
                installers = [User.objects.get(id=options['installer'], role='installer')]
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Монтажник с ID {options["installer"]} не найден')
                )
                return
        else:
            # Получаем всех монтажников, у которых есть расписания
            installers = User.objects.filter(
                role='installer',
                installation_orders__schedule__scheduled_date=target_date,
                installation_orders__schedule__status='scheduled'
            ).distinct()

        if not installers:
            self.stdout.write(
                self.style.WARNING(f'Нет монтажников с расписаниями на {target_date}')
            )
            return

        # Оптимизируем маршруты
        optimized_count = 0
        for installer in installers:
            self.stdout.write(f'Оптимизация маршрута для {installer.get_full_name()}...')
            
            try:
                # Проверяем, есть ли расписания на эту дату
                schedules_count = InstallationSchedule.objects.filter(
                    installers=installer,
                    scheduled_date=target_date,
                    status='scheduled'
                ).count()

                if schedules_count == 0:
                    self.stdout.write(
                        self.style.WARNING(f'  Нет расписаний для {installer.get_full_name()} на {target_date}')
                    )
                    continue

                # Выполняем оптимизацию
                route = RouteOptimizationService.optimize_daily_route(installer.id, target_date)
                
                if route:
                    optimized_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Маршрут оптимизирован: {schedules_count} монтажей, '
                            f'общее расстояние: {route.total_distance:.1f} км'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'  Не удалось оптимизировать маршрут для {installer.get_full_name()}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  Ошибка при оптимизации для {installer.get_full_name()}: {str(e)}')
                )

        # Итоговая статистика
        self.stdout.write(
            self.style.SUCCESS(f'\nОптимизация завершена: {optimized_count} маршрутов оптимизировано')
        )

        # Если указано несколько дней вперед
        if options['days_ahead'] > 1:
            self.stdout.write(f'\nОптимизация на {options["days_ahead"]} дней вперед...')
            
            for day_offset in range(1, options['days_ahead']):
                future_date = target_date + timedelta(days=day_offset)
                self.stdout.write(f'\nОптимизация на {future_date}:')
                
                future_installers = User.objects.filter(
                    role='installer',
                    installation_orders__schedule__scheduled_date=future_date,
                    installation_orders__schedule__status='scheduled'
                ).distinct()
                
                for installer in future_installers:
                    try:
                        route = RouteOptimizationService.optimize_daily_route(installer.id, future_date)
                        if route:
                            schedules_count = route.schedules.count()
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✓ {installer.get_full_name()}: {schedules_count} монтажей, '
                                    f'{route.total_distance:.1f} км'
                                )
                            )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  Ошибка для {installer.get_full_name()}: {str(e)}')
                        )