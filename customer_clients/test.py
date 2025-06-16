# customer_clients/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Client as CustomerClient
from .forms import ClientForm

User = get_user_model()


class ClientModelTests(TestCase):
    """Тесты модели Client"""
    
    def setUp(self):
        self.client_data = {
            'name': 'Иван Петров',
            'address': 'ул. Тестовая, 123',
            'phone': '+7900123456',
            'source': 'website'
        }
    
    def test_create_client(self):
        """Тест создания клиента"""
        client = CustomerClient.objects.create(**self.client_data)
        self.assertEqual(client.name, 'Иван Петров')
        self.assertEqual(client.source, 'website')
        self.assertEqual(str(client), 'Иван Петров (+7900123456)')
    
    def test_client_source_choices(self):
        """Тест вариантов источников клиентов"""
        valid_sources = ['avito', 'vk', 'website', 'recommendations', 'other']
        
        for source in valid_sources:
            client = CustomerClient.objects.create(
                name=f'Client {source}',
                address='Test address',
                phone='+7900123456',
                source=source
            )
            self.assertEqual(client.source, source)
    
    def test_client_ordering(self):
        """Тест сортировки клиентов"""
        # Создаем клиентов с разным временем
        client1 = CustomerClient.objects.create(
            name='Client 1',
            address='Address 1',
            phone='+7900123451',
            source='website'
        )
        
        client2 = CustomerClient.objects.create(
            name='Client 2',
            address='Address 2',
            phone='+7900123452',
            source='avito'
        )
        
        # По умолчанию сортировка по -created_at
        clients = CustomerClient.objects.all()
        self.assertEqual(clients[0], client2)  # Последний созданный должен быть первым
        self.assertEqual(clients[1], client1)
    
    def test_client_verbose_names(self):
        """Тест verbose_name модели"""
        self.assertEqual(CustomerClient._meta.verbose_name, 'Клиент')
        self.assertEqual(CustomerClient._meta.verbose_name_plural, 'Клиенты')


class ClientViewsTests(TestCase):
    """Тесты представлений клиентов"""
    
    def setUp(self):
        self.client_http = Client()
        
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
        
        # Создаем тестовых клиентов
        self.customer1 = CustomerClient.objects.create(
            name='Иван Петров',
            address='ул. Тестовая, 123',
            phone='+7900123456',
            source='website'
        )
        
        self.customer2 = CustomerClient.objects.create(
            name='Мария Сидорова',
            address='пр. Главный, 456',
            phone='+7900654321',
            source='avito'
        )
    
    def test_client_list_view_requires_login(self):
        """Тест доступа к списку клиентов без авторизации"""
        response = self.client_http.get(reverse('client_list'))
        self.assertRedirects(response, '/user_accounts/login/?next=/clients/')
    
    def test_client_list_view_authenticated(self):
        """Тест списка клиентов для авторизованного пользователя"""
        self.client_http.login(username='manager', password='testpass123')
        response = self.client_http.get(reverse('client_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Иван Петров')
        self.assertContains(response, 'Мария Сидорова')
    
    def test_client_list_filter_by_source(self):
        """Тест фильтрации клиентов по источнику"""
        self.client_http.login(username='manager', password='testpass123')
        response = self.client_http.get(reverse('client_list') + '?source=website')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Иван Петров')
        self.assertNotContains(response, 'Мария Сидорова')
    
    def test_client_list_search(self):
        """Тест поиска клиентов"""
        self.client_http.login(username='manager', password='testpass123')
        response = self.client_http.get(reverse('client_list') + '?search=Иван')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Иван Петров')
        self.assertNotContains(response, 'Мария Сидорова')
    
    def test_client_detail_view(self):
        """Тест детального просмотра клиента"""
        self.client_http.login(username='manager', password='testpass123')
        response = self.client_http.get(reverse('client_detail', kwargs={'pk': self.customer1.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Иван Петров')
        self.assertContains(response, 'ул. Тестовая, 123')
        self.assertContains(response, '+7900123456')
    
    def test_client_new_view_permissions(self):
        """Тест прав доступа к созданию клиентов"""
        # Монтажник не должен создавать клиентов
        self.client_http.login(username='installer', password='testpass123')
        response = self.client_http.get(reverse('client_new'))
        self.assertRedirects(response, reverse('client_list'))
        
        # Менеджер должен создавать клиентов
        self.client_http.login(username='manager', password='testpass123')
        response = self.client_http.get(reverse('client_new'))
        self.assertEqual(response.status_code, 200)
        
        # Владелец должен создавать клиентов
        self.client_http.login(username='owner', password='testpass123')
        response = self.client_http.get(reverse('client_new'))
        self.assertEqual(response.status_code, 200)
    
    def test_client_create_post(self):
        """Тест создания клиента через POST"""
        self.client_http.login(username='manager', password='testpass123')
        
        client_data = {
            'name': 'Новый Клиент',
            'address': 'ул. Новая, 789',
            'phone': '+7900999888',
            'source': 'recommendations'
        }
        
        response = self.client_http.post(reverse('client_new'), client_data)
        
        # Должен быть редирект после создания
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что клиент создан
        client = CustomerClient.objects.get(name='Новый Клиент')
        self.assertEqual(client.phone, '+7900999888')
        self.assertEqual(client.source, 'recommendations')
    
    def test_client_edit_permissions(self):
        """Тест прав доступа к редактированию клиентов"""
        # Монтажник не должен редактировать клиентов
        self.client_http.login(username='installer', password='testpass123')
        response = self.client_http.get(reverse('client_edit', kwargs={'pk': self.customer1.pk}))
        self.assertRedirects(response, reverse('client_list'))
        
        # Менеджер должен редактировать клиентов
        self.client_http.login(username='manager', password='testpass123')
        response = self.client_http.get(reverse('client_edit', kwargs={'pk': self.customer1.pk}))
        self.assertEqual(response.status_code, 200)
    
    def test_client_edit_post(self):
        """Тест редактирования клиента через POST"""
        self.client_http.login(username='manager', password='testpass123')
        
        updated_data = {
            'name': 'Иван Обновленный',
            'address': 'ул. Обновленная, 123',
            'phone': '+7900123456',
            'source': 'vk'
        }
        
        response = self.client_http.post(
            reverse('client_edit', kwargs={'pk': self.customer1.pk}),
            updated_data
        )
        
        # Должен быть редирект после обновления
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что клиент обновлен
        self.customer1.refresh_from_db()
        self.assertEqual(self.customer1.name, 'Иван Обновленный')
        self.assertEqual(self.customer1.source, 'vk')


class ClientAPITests(APITestCase):
    """Тесты API клиентов"""
    
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
        
        self.customer = CustomerClient.objects.create(
            name='API Клиент',
            address='API адрес',
            phone='+7900111222',
            source='website'
        )
    
    def test_client_list_api_permissions(self):
        """Тест прав доступа к API списка клиентов"""
        # Неавторизованный доступ
        response = self.client.get('/api/clients/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Авторизованный доступ
        self.client.force_authenticate(user=self.manager)
        response = self.client.get('/api/clients/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_client_create_api(self):
        """Тест создания клиента через API"""
        self.client.force_authenticate(user=self.manager)
        
        client_data = {
            'name': 'API Новый Клиент',
            'address': 'API Новый адрес',
            'phone': '+7900333444',
            'source': 'avito'
        }
        
        response = self.client.post('/api/clients/', client_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Проверяем, что клиент создан
        client = CustomerClient.objects.get(name='API Новый Клиент')
        self.assertEqual(client.source, 'avito')
    
    def test_client_create_api_installer_forbidden(self):
        """Тест запрета создания клиента монтажником через API"""
        self.client.force_authenticate(user=self.installer)
        
        client_data = {
            'name': 'Запрещенный Клиент',
            'address': 'Запрещенный адрес',
            'phone': '+7900555666',
            'source': 'other'
        }
        
        response = self.client.post('/api/clients/', client_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_client_update_api(self):
        """Тест обновления клиента через API"""
        self.client.force_authenticate(user=self.manager)
        
        update_data = {
            'name': 'API Обновленный Клиент',
            'address': 'API Обновленный адрес',
            'phone': '+7900111222',
            'source': 'recommendations'
        }
        
        response = self.client.put(f'/api/clients/{self.customer.pk}/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, 'API Обновленный Клиент')
        self.assertEqual(self.customer.source, 'recommendations')
    
    def test_client_filter_api(self):
        """Тест фильтрации клиентов через API"""
        # Создаем дополнительного клиента с другим источником
        CustomerClient.objects.create(
            name='VK Клиент',
            address='VK адрес',
            phone='+7900777888',
            source='vk'
        )
        
        self.client.force_authenticate(user=self.manager)
        
        # Фильтр по источнику
        response = self.client.get('/api/clients/?source=website')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['source'], 'website')
    
    def test_client_search_api(self):
        """Тест поиска клиентов через API"""
        self.client.force_authenticate(user=self.manager)
        
        response = self.client.get('/api/clients/?search=API')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('API', response.data['results'][0]['name'])


class ClientFormsTests(TestCase):
    """Тесты форм клиентов"""
    
    def test_client_form_valid(self):
        """Тест валидной формы клиента"""
        form_data = {
            'name': 'Тест Клиент',
            'address': 'Тест адрес',
            'phone': '+7900123456',
            'source': 'website'
        }
        
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        client = form.save()
        self.assertEqual(client.name, 'Тест Клиент')
        self.assertEqual(client.source, 'website')
    
    def test_client_form_invalid_source(self):
        """Тест формы с невалидным источником"""
        form_data = {
            'name': 'Тест Клиент',
            'address': 'Тест адрес',
            'phone': '+7900123456',
            'source': 'invalid_source'
        }
        
        form = ClientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('source', form.errors)
    
    def test_client_form_required_fields(self):
        """Тест обязательных полей формы"""
        form_data = {}
        form = ClientForm(data=form_data)
        self.assertFalse(form.is_valid())
        
        required_fields = ['name', 'address', 'phone', 'source']
        for field in required_fields:
            self.assertIn(field, form.errors)


class ClientIntegrationTests(TestCase):
    """Интеграционные тесты клиентов"""
    
    def setUp(self):
        self.client_http = Client()
        
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
    
    def test_client_lifecycle_manager(self):
        """Тест полного жизненного цикла клиента для менеджера"""
        self.client_http.login(username='manager', password='testpass123')
        
        # 1. Создание клиента
        client_data = {
            'name': 'Жизненный Цикл Клиент',
            'address': 'ул. Цикловая, 123',
            'phone': '+7900987654',
            'source': 'website'
        }
        
        response = self.client_http.post(reverse('client_new'), client_data)
        self.assertEqual(response.status_code, 302)
        
        client = CustomerClient.objects.get(name='Жизненный Цикл Клиент')
        
        # 2. Просмотр клиента
        response = self.client_http.get(reverse('client_detail', kwargs={'pk': client.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Жизненный Цикл Клиент')
        
        # 3. Редактирование клиента
        updated_data = {
            'name': 'Обновленный Клиент',
            'address': 'ул. Обновленная, 456',
            'phone': '+7900987654',
            'source': 'avito'
        }
        
        response = self.client_http.post(
            reverse('client_edit', kwargs={'pk': client.pk}),
            updated_data
        )
        self.assertEqual(response.status_code, 302)
        
        client.refresh_from_db()
        self.assertEqual(client.name, 'Обновленный Клиент')
        self.assertEqual(client.source, 'avito')
        
        # 4. Проверка в списке
        response = self.client_http.get(reverse('client_list'))
        self.assertContains(response, 'Обновленный Клиент')
    
    def test_installer_view_restrictions(self):
        """Тест ограничений просмотра для монтажника"""
        # Создаем клиента от имени менеджера
        self.client_http.login(username='manager', password='testpass123')
        
        client_data = {
            'name': 'Клиент для Монтажника',
            'address': 'Адрес для теста',
            'phone': '+7900111333',
            'source': 'vk'
        }
        
        response = self.client_http.post(reverse('client_new'), client_data)
        client = CustomerClient.objects.get(name='Клиент для Монтажника')
        
        # Переключаемся на монтажника
        self.client_http.login(username='installer', password='testpass123')
        
        # Монтажник может просматривать клиентов
        response = self.client_http.get(reverse('client_list'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client_http.get(reverse('client_detail', kwargs={'pk': client.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Но не может создавать или редактировать
        response = self.client_http.get(reverse('client_new'))
        self.assertEqual(response.status_code, 302)  # Редирект
        
        response = self.client_http.get(reverse('client_edit', kwargs={'pk': client.pk}))
        self.assertEqual(response.status_code, 302)  # Редирект
    
    def test_client_search_and_filter_integration(self):
        """Тест интеграции поиска и фильтрации"""
        self.client_http.login(username='manager', password='testpass123')
        
        # Создаем разных клиентов
        clients_data = [
            {'name': 'Иван Поиск', 'address': 'адрес1', 'phone': '+7900001111', 'source': 'website'},
            {'name': 'Петр Поиск', 'address': 'адрес2', 'phone': '+7900002222', 'source': 'avito'},
            {'name': 'Мария Тест', 'address': 'адрес3', 'phone': '+7900003333', 'source': 'website'},
        ]
        
        for data in clients_data:
            CustomerClient.objects.create(**data)
        
        # Поиск по имени
        response = self.client_http.get(reverse('client_list') + '?search=Поиск')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Иван Поиск')
        self.assertContains(response, 'Петр Поиск')
        self.assertNotContains(response, 'Мария Тест')
        
        # Фильтр по источнику
        response = self.client_http.get(reverse('client_list') + '?source=website')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Иван Поиск')
        self.assertNotContains(response, 'Петр Поиск')
        self.assertContains(response, 'Мария Тест')
        
        # Комбинированный поиск и фильтр
        response = self.client_http.get(reverse('client_list') + '?search=Поиск&source=website')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Иван Поиск')
        self.assertNotContains(response, 'Петр Поиск')
        self.assertNotContains(response, 'Мария Тест')


class ClientModelValidationTests(TestCase):
    """Тесты валидации модели клиента"""
    
    def test_client_string_representation(self):
        """Тест строкового представления клиента"""
        client = CustomerClient.objects.create(
            name='Тест Представление',
            address='Тест адрес',
            phone='+7900123789',
            source='other'
        )
        
        expected_str = 'Тест Представление (+7900123789)'
        self.assertEqual(str(client), expected_str)
    
    def test_client_source_display(self):
        """Тест отображения источников клиентов"""
        sources_mapping = {
            'avito': 'Авито',
            'vk': 'ВК',
            'website': 'Сайт',
            'recommendations': 'Рекомендации',
            'other': 'Другое',
        }
        
        for source_code, source_display in sources_mapping.items():
            client = CustomerClient.objects.create(
                name=f'Клиент {source_code}',
                address='Тест адрес',
                phone=f'+790012345{source_code[:1]}',
                source=source_code
            )
            
            self.assertEqual(client.get_source_display(), source_display)
    
    def test_client_creation_timestamp(self):
        """Тест автоматического создания timestamp"""
        client = CustomerClient.objects.create(
            name='Timestamp Test',
            address='Timestamp address',
            phone='+7900999111',
            source='website'
        )
        
        self.assertIsNotNone(client.created_at)
        
        # Создаем второго клиента и проверяем, что время отличается
        from django.utils import timezone
        import time
        time.sleep(0.1)  # Небольшая задержка
        
        client2 = CustomerClient.objects.create(
            name='Timestamp Test 2',
            address='Timestamp address 2',
            phone='+7900999222',
            source='avito'
        )
        
        self.assertGreater(client2.created_at, client.created_at)