# services/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from .models import Service
from .forms import ServiceForm

User = get_user_model()


class ServiceModelTests(TestCase):
    """Тесты модели Service"""
    
    def setUp(self):
        self.service_data = {
            'name': 'Установка кондиционера 12000 BTU',
            'cost_price': Decimal('15000.00'),
            'selling_price': Decimal('25000.00'),
            'category': 'conditioner'
        }
    
    def test_create_service(self):
        """Тест создания услуги"""
        service = Service.objects.create(**self.service_data)
        self.assertEqual(service.name, 'Установка кондиционера 12000 BTU')
        self.assertEqual(service.cost_price, Decimal('15000.00'))
        self.assertEqual(service.selling_price, Decimal('25000.00'))
        self.assertEqual(service.category, 'conditioner')
        self.assertEqual(str(service), 'Установка кондиционера 12000 BTU (Кондиционер)')
    
    def test_service_categories(self):
        """Тест категорий услуг"""
        valid_categories = ['conditioner', 'installation', 'dismantling', 'maintenance', 'additional']
        
        for category in valid_categories:
            service = Service.objects.create(
                name=f'Услуга {category}',
                cost_price=Decimal('1000.00'),
                selling_price=Decimal('1500.00'),
                category=category
            )
            self.assertEqual(service.category, category)
    
    def test_service_category_display(self):
        """Тест отображения категорий"""
        categories_mapping = {
            'conditioner': 'Кондиционер',
            'installation': 'Монтаж',
            'dismantling': 'Демонтаж',
            'maintenance': 'Обслуживание',
            'additional': 'Доп услуга',
        }
        
        for category_code, category_display in categories_mapping.items():
            service = Service.objects.create(
                name=f'Тест {category_code}',
                cost_price=Decimal('1000.00'),
                selling_price=Decimal('1500.00'),
                category=category_code
            )
            self.assertEqual(service.get_category_display(), category_display)
    
    def test_service_profit_calculation(self):
        """Тест расчета прибыли (если будет добавлен метод)"""
        service = Service.objects.create(**self.service_data)
        expected_profit = service.selling_price - service.cost_price
        self.assertEqual(expected_profit, Decimal('10000.00'))
    
    def test_service_verbose_names(self):
        """Тест verbose_name модели"""
        self.assertEqual(Service._meta.verbose_name, 'Услуга')
        self.assertEqual(Service._meta.verbose_name_plural, 'Услуги')


class ServiceViewsTests(TestCase):
    """Тесты представлений услуг"""
    
    def setUp(self):
        self.client = Client()
        
        # Создаем пользователей
        self.owner = User.objects.create_user(
            username='owner',
            password='testpass123',
            role='owner'
        )
        
        self.manager = User.objects.create_user(
            username='manager',
            password='testpass123',
            role='manager'
        )
        
        self.installer = User.objects.create_user(
            username='installer',
            password='testpass123',
            role='installer'
        )
        
        # Создаем тестовые услуги
        self.service1 = Service.objects.create(
            name='Кондиционер LG 12000',
            cost_price=Decimal('15000.00'),
            selling_price=Decimal('25000.00'),
            category='conditioner'
        )
        
        self.service2 = Service.objects.create(
            name='Монтаж кондиционера',
            cost_price=Decimal('2000.00'),
            selling_price=Decimal('5000.00'),
            category='installation'
        )
    
    def test_service_list_view_requires_login(self):
        """Тест доступа к списку услуг без авторизации"""
        response = self.client.get(reverse('service_list'))
        self.assertRedirects(response, '/user_accounts/login/?next=/services/')
    
    def test_service_list_view_authenticated(self):
        """Тест списка услуг для авторизованного пользователя"""
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('service_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Кондиционер LG 12000')
        self.assertContains(response, 'Монтаж кондиционера')
    
    def test_service_list_filter_by_category(self):
        """Тест фильтрации услуг по категории"""
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('service_list') + '?category=conditioner')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Кондиционер LG 12000')
        self.assertNotContains(response, 'Монтаж кондиционера')
    
    def test_service_detail_view(self):
        """Тест детального просмотра услуги"""
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('service_detail', kwargs={'pk': self.service1.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Кондиционер LG 12000')
        self.assertContains(response, '15000.00')
        self.assertContains(response, '25000.00')
    
    def test_service_new_view_permissions(self):
        """Тест прав доступа к созданию услуг"""
        # Менеджер не должен создавать услуги
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('service_new'))
        self.assertRedirects(response, reverse('service_list'))
        
        # Монтажник не должен создавать услуги
        self.client.login(username='installer', password='testpass123')
        response = self.client.get(reverse('service_new'))
        self.assertRedirects(response, reverse('service_list'))
        
        # Владелец должен создавать услуги
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('service_new'))
        self.assertEqual(response.status_code, 200)
    
    def test_service_create_post(self):
        """Тест создания услуги через POST"""
        self.client.login(username='owner', password='testpass123')
        
        service_data = {
            'name': 'Новая услуга',
            'cost_price': '3000.00',
            'selling_price': '6000.00',
            'category': 'maintenance'
        }
        
        response = self.client.post(reverse('service_new'), service_data)
        
        # Должен быть редирект после создания
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что услуга создана
        service = Service.objects.get(name='Новая услуга')
        self.assertEqual(service.cost_price, Decimal('3000.00'))
        self.assertEqual(service.category, 'maintenance')
    
    def test_service_edit_permissions(self):
        """Тест прав доступа к редактированию услуг"""
        # Менеджер не должен редактировать услуги
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('service_edit', kwargs={'pk': self.service1.pk}))
        self.assertRedirects(response, reverse('service_list'))
        
        # Владелец должен редактировать услуги
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('service_edit', kwargs={'pk': self.service1.pk}))
        self.assertEqual(response.status_code, 200)
    
    def test_service_edit_post(self):
        """Тест редактирования услуги через POST"""
        self.client.login(username='owner', password='testpass123')
        
        updated_data = {
            'name': 'Обновленная услуга',
            'cost_price': '16000.00',
            'selling_price': '26000.00',
            'category': 'conditioner'
        }
        
        response = self.client.post(
            reverse('service_edit', kwargs={'pk': self.service1.pk}),
            updated_data
        )
        
        # Должен быть редирект после обновления
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что услуга обновлена
        self.service1.refresh_from_db()
        self.assertEqual(self.service1.name, 'Обновленная услуга')
        self.assertEqual(self.service1.cost_price, Decimal('16000.00'))


class ServiceAPITests(APITestCase):
    """Тесты API услуг"""
    
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            password='testpass123',
            role='owner'
        )
        
        self.manager = User.objects.create_user(
            username='manager',
            password='testpass123',
            role='manager'
        )
        
        self.installer = User.objects.create_user(
            username='installer',
            password='testpass123',
            role='installer'
        )
        
        self.service = Service.objects.create(
            name='API Услуга',
            cost_price=Decimal('1000.00'),
            selling_price=Decimal('2000.00'),
            category='additional'
        )
    
    def test_service_list_api_permissions(self):
        """Тест прав доступа к API списка услуг"""
        # Неавторизованный доступ
        response = self.client.get('/api/services/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Авторизованный доступ
        self.client.force_authenticate(user=self.manager)
        response = self.client.get('/api/services/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_service_create_api_owner_only(self):
        """Тест создания услуги через API - только владелец"""
        service_data = {
            'name': 'API Новая Услуга',
            'cost_price': '1500.00',
            'selling_price': '3000.00',
            'category': 'dismantling'
        }
        
        # Менеджер не может создавать
        self.client.force_authenticate(user=self.manager)
        response = self.client.post('/api/services/', service_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Владелец может создавать
        self.client.force_authenticate(user=self.owner)
        response = self.client.post('/api/services/', service_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Проверяем, что услуга создана
        service = Service.objects.get(name='API Новая Услуга')
        self.assertEqual(service.category, 'dismantling')
    
    def test_service_update_api_owner_only(self):
        """Тест обновления услуги через API - только владелец"""
        update_data = {
            'name': 'API Обновленная Услуга',
            'cost_price': '1200.00',
            'selling_price': '2500.00',
            'category': 'maintenance'
        }
        
        # Менеджер не может обновлять
        self.client.force_authenticate(user=self.manager)
        response = self.client.put(f'/api/services/{self.service.pk}/', update_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Владелец может обновлять
        self.client.force_authenticate(user=self.owner)
        response = self.client.put(f'/api/services/{self.service.pk}/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.service.refresh_from_db()
        self.assertEqual(self.service.name, 'API Обновленная Услуга')
        self.assertEqual(self.service.category, 'maintenance')
    
    def test_service_filter_api(self):
        """Тест фильтрации услуг через API"""
        # Создаем дополнительную услугу
        Service.objects.create(
            name='Фильтр Услуга',
            cost_price=Decimal('500.00'),
            selling_price=Decimal('1000.00'),
            category='installation'
        )
        
        self.client.force_authenticate(user=self.manager)
        
        # Фильтр по категории
        response = self.client.get('/api/services/?category=additional')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['category'], 'additional')
    
    def test_service_search_api(self):
        """Тест поиска услуг через API"""
        self.client.force_authenticate(user=self.manager)
        
        response = self.client.get('/api/services/?search=API')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('API', response.data['results'][0]['name'])


class ServiceFormsTests(TestCase):
    """Тесты форм услуг"""
    
    def test_service_form_valid(self):
        """Тест валидной формы услуги"""
        form_data = {
            'name': 'Тест Услуга',
            'cost_price': '1000.00',
            'selling_price': '2000.00',
            'category': 'maintenance'
        }
        
        form = ServiceForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        service = form.save()
        self.assertEqual(service.name, 'Тест Услуга')
        self.assertEqual(service.cost_price, Decimal('1000.00'))
        self.assertEqual(service.category, 'maintenance')
    
    def test_service_form_invalid_category(self):
        """Тест формы с невалидной категорией"""
        form_data = {
            'name': 'Тест Услуга',
            'cost_price': '1000.00',
            'selling_price': '2000.00',
            'category': 'invalid_category'
        }
        
        form = ServiceForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)
    
    def test_service_form_required_fields(self):
        """Тест обязательных полей формы"""
        form_data = {}
        form = ServiceForm(data=form_data)
        self.assertFalse(form.is_valid())
        
        required_fields = ['name', 'cost_price', 'selling_price', 'category']
        for field in required_fields:
            self.assertIn(field, form.errors)
    
    def test_service_form_negative_prices(self):
        """Тест формы с отрицательными ценами"""
        form_data = {
            'name': 'Тест Услуга',
            'cost_price': '-1000.00',
            'selling_price': '2000.00',
            'category': 'maintenance'
        }
        
        form = ServiceForm(data=form_data)
        # Django автоматически валидирует DecimalField на отрицательные значения
        # если не указан min_value
        self.assertFalse(form.is_valid())


class ServiceIntegrationTests(TestCase):
    """Интеграционные тесты услуг"""
    
    def setUp(self):
        self.client = Client()
        
        self.owner = User.objects.create_user(
            username='owner',
            password='testpass123',
            role='owner'
        )
        
        self.manager = User.objects.create_user(
            username='manager',
            password='testpass123',
            role='manager'
        )
    
    def test_service_lifecycle_owner(self):
        """Тест полного жизненного цикла услуги для владельца"""
        self.client.login(username='owner', password='testpass123')
        
        # 1. Создание услуги
        service_data = {
            'name': 'Жизненный Цикл Услуга',
            'cost_price': '5000.00',
            'selling_price': '10000.00',
            'category': 'conditioner'
        }
        
        response = self.client.post(reverse('service_new'), service_data)
        self.assertEqual(response.status_code, 302)
        
        service = Service.objects.get(name='Жизненный Цикл Услуга')
        
        # 2. Просмотр услуги
        response = self.client.get(reverse('service_detail', kwargs={'pk': service.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Жизненный Цикл Услуга')
        
        # 3. Редактирование услуги
        updated_data = {
            'name': 'Обновленная Услуга',
            'cost_price': '6000.00',
            'selling_price': '12000.00',
            'category': 'installation'
        }
        
        response = self.client.post(
            reverse('service_edit', kwargs={'pk': service.pk}),
            updated_data
        )
        self.assertEqual(response.status_code, 302)
        
        service.refresh_from_db()
        self.assertEqual(service.name, 'Обновленная Услуга')
        self.assertEqual(service.cost_price, Decimal('6000.00'))
        self.assertEqual(service.category, 'installation')
        
        # 4. Проверка в списке
        response = self.client.get(reverse('service_list'))
        self.assertContains(response, 'Обновленная Услуга')
    
    def test_manager_view_restrictions(self):
        """Тест ограничений для менеджера"""
        # Создаем услугу от имени владельца
        self.client.login(username='owner', password='testpass123')
        
        service_data = {
            'name': 'Услуга для Менеджера',
            'cost_price': '2000.00',
            'selling_price': '4000.00',
            'category': 'additional'
        }
        
        response = self.client.post(reverse('service_new'), service_data)
        service = Service.objects.get(name='Услуга для Менеджера')
        
        # Переключаемся на менеджера
        self.client.login(username='manager', password='testpass123')
        
        # Менеджер может просматривать услуги
        response = self.client.get(reverse('service_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Услуга для Менеджера')
        
        response = self.client.get(reverse('service_detail', kwargs={'pk': service.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Но не может создавать или редактировать
        response = self.client.get(reverse('service_new'))
        self.assertEqual(response.status_code, 302)  # Редирект с сообщением об ошибке
        
        response = self.client.get(reverse('service_edit', kwargs={'pk': service.pk}))
        self.assertEqual(response.status_code, 302)  # Редирект с сообщением об ошибке
    
    def test_service_category_filter_integration(self):
        """Тест интеграции фильтрации по категориям"""
        self.client.login(username='owner', password='testpass123')
        
        # Создаем услуги разных категорий
        services_data = [
            {'name': 'Кондиционер 1', 'cost_price': '15000', 'selling_price': '25000', 'category': 'conditioner'},
            {'name': 'Кондиционер 2', 'cost_price': '20000', 'selling_price': '30000', 'category': 'conditioner'},
            {'name': 'Монтаж 1', 'cost_price': '3000', 'selling_price': '6000', 'category': 'installation'},
            {'name': 'Обслуживание 1', 'cost_price': '1000', 'selling_price': '3000', 'category': 'maintenance'},
        ]
        
        for data in services_data:
            Service.objects.create(**data)
        
        # Проверяем фильтрацию по кондиционерам
        response = self.client.get(reverse('service_list') + '?category=conditioner')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Кондиционер 1')
        self.assertContains(response, 'Кондиционер 2')
        self.assertNotContains(response, 'Монтаж 1')
        self.assertNotContains(response, 'Обслуживание 1')
        
        # Проверяем фильтрацию по монтажу
        response = self.client.get(reverse('service_list') + '?category=installation')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Монтаж 1')
        self.assertNotContains(response, 'Кондиционер 1')
        self.assertNotContains(response, 'Обслуживание 1')


class ServiceBusinessLogicTests(TestCase):
    """Тесты бизнес-логики услуг"""
    
    def test_service_profit_margin(self):
        """Тест расчета маржи прибыли"""
        service = Service.objects.create(
            name='Тест Маржа',
            cost_price=Decimal('10000.00'),
            selling_price=Decimal('15000.00'),
            category='conditioner'
        )
        
        profit = service.selling_price - service.cost_price
        margin_percentage = (profit / service.selling_price) * 100
        
        self.assertEqual(profit, Decimal('5000.00'))
        self.assertEqual(round(margin_percentage, 2), Decimal('33.33'))
    
    def test_service_categories_business_rules(self):
        """Тест бизнес-правил для категорий услуг"""
        # Кондиционеры обычно дорогие
        conditioner = Service.objects.create(
            name='Дорогой кондиционер',
            cost_price=Decimal('50000.00'),
            selling_price=Decimal('75000.00'),
            category='conditioner'
        )
        
        # Дополнительные услуги обычно дешевые
        additional = Service.objects.create(
            name='Чистка фильтров',
            cost_price=Decimal('500.00'),
            selling_price=Decimal('1500.00'),
            category='additional'
        )
        
        # Проверяем логику ценообразования
        conditioner_margin = ((conditioner.selling_price - conditioner.cost_price) / conditioner.selling_price) * 100
        additional_margin = ((additional.selling_price - additional.cost_price) / additional.selling_price) * 100
        
        # У дополнительных услуг обычно больше маржа
        self.assertGreater(additional_margin, conditioner_margin)
    
    def test_service_creation_timestamp(self):
        """Тест автоматического создания timestamp"""
        service = Service.objects.create(
            name='Timestamp Test',
            cost_price=Decimal('1000.00'),
            selling_price=Decimal('2000.00'),
            category='maintenance'
        )
        
        self.assertIsNotNone(service.created_at)
        
        # Создаем вторую услугу и проверяем, что время отличается
        import time
        time.sleep(0.1)
        
        service2 = Service.objects.create(
            name='Timestamp Test 2',
            cost_price=Decimal('1500.00'),
            selling_price=Decimal('2500.00'),
            category='additional'
        )
        
        self.assertGreater(service2.created_at, service.created_at)


class ServiceAdminTests(TestCase):
    """Тесты админ-панели для услуг"""
    
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            password='testpass123',
            role='owner',
            is_staff=True,
            is_superuser=True
        )
        
        self.service = Service.objects.create(
            name='Админ Тест Услуга',
            cost_price=Decimal('2000.00'),
            selling_price=Decimal('4000.00'),
            category='dismantling'
        )
    
    def test_service_admin_list_display(self):
        """Тест отображения списка услуг в админке"""
        from django.contrib.admin.sites import AdminSite
        from services.admin import ServiceAdmin
        
        admin_site = AdminSite()
        service_admin = ServiceAdmin(Service, admin_site)
        
        # Проверяем поля отображения
        expected_fields = ('name', 'category', 'cost_price', 'selling_price', 'created_at')
        self.assertEqual(service_admin.list_display, expected_fields)
    
    def test_service_admin_filters(self):
        """Тест фильтров в админке"""
        from django.contrib.admin.sites import AdminSite
        from services.admin import ServiceAdmin
        
        admin_site = AdminSite()
        service_admin = ServiceAdmin(Service, admin_site)
        
        # Проверяем фильтры
        expected_filters = ('category', 'created_at')
        self.assertEqual(service_admin.list_filter, expected_filters)


class ServicePerformanceTests(TestCase):
    """Тесты производительности для услуг"""
    
    def test_bulk_service_creation(self):
        """Тест массового создания услуг"""
        services_data = []
        
        # Создаем данные для 100 услуг
        for i in range(100):
            services_data.append(Service(
                name=f'Массовая услуга {i}',
                cost_price=Decimal(f'{1000 + i}.00'),
                selling_price=Decimal(f'{2000 + i}.00'),
                category='additional'
            ))
        
        # Массовое создание
        services = Service.objects.bulk_create(services_data)
        
        self.assertEqual(len(services), 100)
        self.assertEqual(Service.objects.count(), 100)
    
    def test_service_queryset_optimization(self):
        """Тест оптимизации запросов"""
        # Создаем несколько услуг
        for i in range(10):
            Service.objects.create(
                name=f'Оптимизация {i}',
                cost_price=Decimal('1000.00'),
                selling_price=Decimal('2000.00'),
                category='maintenance'
            )
        
        # Проверяем количество запросов при получении списка
        with self.assertNumQueries(1):
            services = list(Service.objects.all())
            
        self.assertEqual(len(services), 10)


class ServiceValidationTests(TestCase):
    """Тесты валидации услуг"""
    
    def test_service_price_validation(self):
        """Тест валидации цен"""
        # Продажная цена должна быть больше себестоимости (бизнес-правило)
        service = Service(
            name='Валидация цен',
            cost_price=Decimal('10000.00'),
            selling_price=Decimal('5000.00'),  # Меньше себестоимости
            category='conditioner'
        )
        
        # В реальном проекте здесь должна быть валидация
        # Пока просто создаем и проверяем, что убыток
        service.save()
        
        profit = service.selling_price - service.cost_price
        self.assertLess(profit, Decimal('0.00'))  # Убыток
    
    def test_service_name_uniqueness(self):
        """Тест уникальности названий услуг"""
        Service.objects.create(
            name='Уникальная услуга',
            cost_price=Decimal('1000.00'),
            selling_price=Decimal('2000.00'),
            category='additional'
        )
        
        # Пытаемся создать услугу с таким же названием
        # В текущей модели это разрешено, но можно добавить ограничение
        duplicate_service = Service.objects.create(
            name='Уникальная услуга',
            cost_price=Decimal('1500.00'),
            selling_price=Decimal('2500.00'),
            category='maintenance'
        )
        
        # Проверяем, что создались обе услуги
        services_count = Service.objects.filter(name='Уникальная услуга').count()
        self.assertEqual(services_count, 2)
    
    def test_service_decimal_precision(self):
        """Тест точности десятичных полей"""
        service = Service.objects.create(
            name='Точность цен',
            cost_price=Decimal('1234.56'),
            selling_price=Decimal('2345.67'),
            category='installation'
        )
        
        # Проверяем, что точность сохранилась
        self.assertEqual(service.cost_price, Decimal('1234.56'))
        self.assertEqual(service.selling_price, Decimal('2345.67'))
        
        # Проверяем, что можем работать с копейками
        service.cost_price = Decimal('1234.99')
        service.save()
        
        service.refresh_from_db()
        self.assertEqual(service.cost_price, Decimal('1234.99'))