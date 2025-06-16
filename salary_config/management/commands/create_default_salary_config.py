# salary_config/management/commands/create_default_salary_config.py
from django.core.management.base import BaseCommand
from django.db import transaction
from salary_config.services import SalaryConfigService
from salary_config.models import SalaryConfig, UserSalaryAssignment
from user_accounts.models import User

class Command(BaseCommand):
    help = 'Создает конфигурацию зарплат по умолчанию и назначает ее всем пользователям'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно создать новую конфигурацию, даже если уже есть активная',
        )
        parser.add_argument(
            '--assign-all',
            action='store_true',
            help='Назначить конфигурацию всем пользователям (включая тех, у кого уже есть)',
        )

    def handle(self, *args, **options):
        self.stdout.write('Создание конфигурации зарплат по умолчанию...')
        
        # Проверяем, есть ли уже активная конфигурация
        existing_config = SalaryConfig.objects.filter(is_active=True).first()
        
        if existing_config and not options['force']:
            self.stdout.write(
                self.style.WARNING(
                    f'Активная конфигурация уже существует: "{existing_config.name}". '
                    'Используйте --force для создания новой.'
                )
            )
            return

        try:
            with transaction.atomic():
                # Создаем конфигурацию по умолчанию
                config = SalaryConfigService.create_default_config()
                
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Создана конфигурация: "{config.name}"')
                )
                
                # Проверяем настройки
                self.stdout.write('\nСозданные настройки:')
                
                if hasattr(config, 'manager_config'):
                    manager_config = config.manager_config
                    self.stdout.write(f'  Менеджеры:')
                    self.stdout.write(f'    - Фиксированная зарплата: {manager_config.fixed_salary} руб.')
                    self.stdout.write(f'    - Бонус за заказ: {manager_config.bonus_per_completed_order} руб.')
                    self.stdout.write(f'    - % с кондиционеров: {manager_config.conditioner_profit_percentage}%')
                
                if hasattr(config, 'installer_config'):
                    installer_config = config.installer_config
                    self.stdout.write(f'  Монтажники:')
                    self.stdout.write(f'    - Оплата за монтаж: {installer_config.payment_per_installation} руб.')
                    self.stdout.write(f'    - % с доп. услуг: {installer_config.additional_services_profit_percentage}%')
                
                if hasattr(config, 'owner_config'):
                    owner_config = config.owner_config
                    self.stdout.write(f'  Владелец:')
                    self.stdout.write(f'    - Доля с монтажа: {owner_config.payment_per_installation} руб.')
                    self.stdout.write(f'    - % от остатка: {owner_config.remaining_profit_percentage}%')
                
                # Назначаем конфигурацию пользователям
                if options['assign_all']:
                    # Назначаем всем пользователям
                    users = User.objects.filter(role__in=['manager', 'installer', 'owner'])
                    assigned_count = 0
                    
                    for user in users:
                        UserSalaryAssignment.objects.update_or_create(
                            user=user,
                            defaults={'config': config}
                        )
                        assigned_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Конфигурация назначена {assigned_count} пользователям')
                    )
                else:
                    # Назначаем только пользователям без конфигурации
                    assigned_count = SalaryConfigService.bulk_assign_default_config()
                    
                    if assigned_count > 0:
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Конфигурация назначена {assigned_count} новым пользователям')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING('Все пользователи уже имеют назначенные конфигурации')
                        )
                
                # Показываем итоговую статистику
                total_users = User.objects.filter(role__in=['manager', 'installer', 'owner']).count()
                assigned_users = UserSalaryAssignment.objects.count()
                
                self.stdout.write(f'\nИтоговая статистика:')
                self.stdout.write(f'  Всего сотрудников: {total_users}')
                self.stdout.write(f'  Имеют конфигурацию: {assigned_users}')
                self.stdout.write(f'  Без конфигурации: {total_users - assigned_users}')
                
                if total_users - assigned_users > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f'\nВнимание: {total_users - assigned_users} пользователей '
                            'все еще без конфигурации зарплаты.'
                        )
                    )
                    self.stdout.write('Используйте --assign-all для назначения всем.')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при создании конфигурации: {str(e)}')
            )
            raise e
        
        self.stdout.write(
            self.style.SUCCESS('\nКонфигурация зарплат успешно создана!')
        )