# orders/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from .models import Order, OrderItem
from .forms import OrderForm, OrderItemForm
from customer_clients.models import Client as CustomerClient
from services.models import Service
from finance.models import Transaction

User = get_user_model()


class OrderModelTests(TestCase):
    """Тесты модели Order"""
    
    def setUp(self):
        # Создаем пользователей
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
        
        # Создаем клиента
        self.client_obj = CustomerClient.objects.create(
            name='Тест Клиент',
            address='ул. Тестовая, 123',
            phone='+7900123456',
            source='website'
        )
        
        # Создаем услуги
        self.service1 = Service.objects.create(
            name='Кондиционер',
            cost_price=Decimal('15000.00'),
            selling_price=Decimal('25000.00'),
            category='conditioner'
        )
        
        self.service2 = Service.objects.create(
            name='Монтаж',
            cost_price=Decimal('2000.00'),
            selling_price=Decimal('5000.00'),
            category='installation'
        )
    
    def test_create_order(self):
        """Тест создания заказа"""
        order = Order.objects.create(
            client=self.client_obj,
            manager=self.manager
        )
        
        self.assertEqual(order.client, self.client_obj)
        self.assertEqual(order.manager, self.manager)
        self.assertEqual(order.status, 'new')
        self.assertEqual(order.total_cost, Decimal('0.00'))
        self.assertEqual(str(order), f'Заказ #{order.id} - Тест Клиент')
    
    def test_order_status_choices(self):
        """Тест статусов заказа"""
        order = Order.objects.create(
            client=self.client_obj,
            manager=self.manager
        )
        
        valid_statuses = ['new', 'in_progress', 'completed']
        
        for status in valid_statuses:
            order.status = status
            order.save()
            self.assertEqual(order.status, status)
    
    def test_order_installers_assignment(self):
        """Тест назначения монтажников"""
        order = Order.objects.create(
            client=self.client_obj,
            manager=self.manager
        )
        
        # Назначаем монтажника
        order.installers.add(self.installer)
        
        self.assertIn(self.installer, order.installers.all())
        self.assertEqual(order.installers.count(), 1)
    
    def test_order_completion_timestamp(self):
        """Тест времени завершения заказа"""
        order = Order.objects.create(
            client=self.client_obj,
            manager=self.manager
        )
        
        # Изначально время завершения не установлено
        self.assertIsNone(order.completed_at)
        
        # Завершаем заказ
        order.status = 'completed'
        order.completed_at = timezone.now()
        order.save()
        
        self.assertEqual(order.status, 'completed')
        self.assertIsNotNone(order.completed_at)


class OrderItemModelTests(TestCase):
    """Тесты модели OrderItem"""
    
    def setUp(self):
        self.manager = User.objects.create_user(
            username='manager',
            password='testpass123',
            role='manager'
        )
        
        self.client_obj = CustomerClient.objects.create(
            name='Тест Клиент',
            address='ул. Тестовая, 123',
            phone='+7900123456',
            source='website'
        )
        
        self.service = Service.objects.create(
            name='Тест Услуга',
            cost_price=Decimal('1000.00'),
            selling_price=Decimal('2000.00'),
            category='additional'
        )
        
        self.order = Order.objects.create(
            client=self.client_obj,
            manager=self.manager
        )
    
    def test_create_order_item(self):
        """Тест создания позиции заказа"""
        item = OrderItem.objects.create(
            order=self.order,
            service=self.service,
            price=Decimal('2500.00'),
            seller=self.manager
        )
        
        self.assertEqual(item.order, self.order)
        self.assertEqual(item.service, self.service)
        self.assertEqual(item.price, Decimal('2500.00'))
        self.assertEqual(item.seller, self.manager)
        self.assertEqual(str(item), 'Тест Услуга - 2500.00')
    
    def test_order_total_cost_update(self):
        """Тест обновления общей стоимости заказа при добавлении позиций"""
        # Изначально стоимость заказа 0
        self.assertEqual(self.order.total_cost, Decimal('0.00'))
        
        # Добавляем первую позицию
        item1 = OrderItem.objects.create(
            order=self.order,
            service=self.service,
            price=Decimal('2000.00'),
            seller=self.manager
        )
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_cost, Decimal('2000.00'))
        
        # Добавляем вторую позицию
        service2 = Service.objects.create(
            name='Вторая услуга',
            cost_price=Decimal('500.00'),
            selling_price=Decimal('1000.00'),
            category='maintenance'
        )
        
        item2 = OrderItem.objects.create(
            order=self.order,
            service=service2,
            price=Decimal('1500.00'),
            seller=self.manager
        )
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_cost, Decimal('3500.00'))


class OrderViewsTests(TestCase):
    """Тесты представлений заказов"""
    
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
        
        # Создаем клиента
        self.customer = CustomerClient.objects.create(
            name='Тест Клиент',
            address='ул. Тестовая, 123',
            phone='+7900123456',
            source='website'
        )
        
        # Создаем услугу
        self.service = Service.objects.create(
            name='Тест Услуга',
            cost_price=Decimal('1000.00'),
            selling_price=Decimal('2000.00'),
            category='installation'
        )
        
        # Создаем заказ
        self.order = Order.objects.create(
            client=self.customer,
            manager=self.manager
        )
        self.order.installers.add(self.installer)
    
    def test_order_list_view_requires_login(self):
        """Тест доступа к списку заказов без авторизации"""
        response = self.client.get(reverse('order_list'))
        self.assertRedirects(response, '/user_accounts/login/?next=/orders/')
    
    def test_order_list_view_owner(self):
        """Тест списка заказов для владельца"""
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('order_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Заказ #{self.order.id}')
        self.assertTrue(response.context['can_edit'])
        self.assertTrue(response.context['can_create'])
    
    def test_order_list_view_manager(self):
        """Тест списка заказов для менеджера"""
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('order_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Заказ #{self.order.id}')
        self.assertTrue(response.context['can_edit'])
        self.assertTrue(response.context['can_create'])
    
    def test_order_list_view_installer(self):
        """Тест списка заказов для монтажника"""
        self.client.login(username='installer', password='testpass123')
        response = self.client.get(reverse('order_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Заказ #{self.order.id}')
        self.assertFalse(response.context['can_edit'])
        self.assertFalse(response.context['can_create'])
    
    def test_order_detail_view(self):
        """Тест детального просмотра заказа"""
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('order_detail', kwargs={'pk': self.order.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Тест Клиент')
        self.assertContains(response, self.manager.get_full_name())
    
    def test_order_new_view_permissions(self):
        """Тест прав доступа к созданию заказов"""
        # Монтажник не должен создавать заказы
        self.client.login(username='installer', password='testpass123')
        response = self.client.get(reverse('order_new'))
        self.assertRedirects(response, reverse('order_list'))
        
        # Менеджер должен создавать заказы
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('order_new'))
        self.assertEqual(response.status_code, 200)
        
        # Владелец должен создавать заказы
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('order_new'))
        self.assertEqual(response.status_code, 200)
    
    def test_order_create_post(self):
        """Тест создания заказа через POST"""
        self.client.login(username='manager', password='testpass123')
        
        order_data = {
            'client': self.customer.pk,
            'manager': self.manager.pk,
            'status': 'new',
            'installers': [self.installer.pk]
        }
        
        response = self.client.post(reverse('order_new'), order_data)
        
        # Должен быть редирект после создания
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что заказ создан
        new_order = Order.objects.filter(client=self.customer).exclude(pk=self.order.pk).first()
        self.assertIsNotNone(new_order)
        self.assertEqual(new_order.manager, self.manager)
    
    def test_order_edit_permissions(self):
        """Тест прав доступа к редактированию заказов"""
        # Монтажник не должен редактировать заказы
        self.client.login(username='installer', password='testpass123')
        response = self.client.get(reverse('order_edit', kwargs={'pk': self.order.pk}))
        self.assertRedirects(response, reverse('order_list'))
        
        # Менеджер должен редактировать свои заказы
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('order_edit', kwargs={'pk': self.order.pk}))
        self.assertEqual(response.status_code, 200)
    
    def test_order_add_item_view(self):
        """Тест добавления позиции в заказ"""
        self.client.login(username='manager', password='testpass123')
        
        item_data = {
            'service': self.service.pk,
            'price': '2500.00',
            'seller': self.manager.pk
        }
        
        response = self.client.post(
            reverse('order_add_item', kwargs={'pk': self.order.pk}),
            item_data
        )
        
        # Должен быть редирект после добавления
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что позиция добавлена
        item = OrderItem.objects.get(order=self.order, service=self.service)
        self.assertEqual(item.price, Decimal('2500.00'))
        
        # Проверяем, что общая стоимость заказа обновилась
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_cost, Decimal('2500.00'))
    
    def test_order_change_status_installer(self):
        """Тест изменения статуса заказа монтажником"""
        self.client.login(username='installer', password='testpass123')
        
        # Монтажник может только завершать заказы
        response = self.client.post(
            reverse('order_change_status', kwargs={'pk': self.order.pk}),
            {'status': 'completed'}
        )
        
        self.assertEqual(response.status_code, 302)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'completed')
        self.assertIsNotNone(self.order.completed_at)
    
    def test_order_change_status_installer_forbidden(self):
        """Тест запрета изменения статуса на другие значения монтажником"""
        self.client.login(username='installer', password='testpass123')
        
        # Монтажник НЕ может менять статус на 'in_progress'
        response = self.client.post(
            reverse('order_change_status', kwargs={'pk': self.order.pk}),
            {'status': 'in_progress'}
        )
        
        # Должен быть редирект с сообщением об ошибке
        self.assertEqual(response.status_code, 302)
        
        # Статус не должен измениться
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'new')
    
    def test_my_orders_installer_view(self):
        """Тест специального представления для монтажников"""
        self.client.login(username='installer', password='testpass123')
        response = self.client.get(reverse('my_orders'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Заказ #{self.order.id}')
        self.assertTrue(response.context['is_installer_view'])
        
        # Проверяем статистику
        self.assertEqual(response.context['total_orders'], 1)
        self.assertEqual(response.context['completed_orders'], 0)
        self.assertEqual(response.context['in_progress_orders'], 0)


class OrderSignalsTests(TestCase):
    """Тесты сигналов заказов"""
    
    def setUp(self):
        self.manager = User.objects.create_user(
            username='manager',
            password='testpass123',
            role='manager'
        )
        
        self.customer = CustomerClient.objects.create(
            name='Сигнал Клиент',
            address='ул. Сигнальная, 123',
            phone='+7900123456',
            source='website'
        )
        
        self.service = Service.objects.create(
            name='Сигнал Услуга',
            cost_price=Decimal('1000.00'),
            selling_price=Decimal('2000.00'),
            category='installation'
        )
        
        self.order = Order.objects.create(
            client=self.customer,
            manager=self.manager
        )
    
    def test_transaction_creation_on_order_completion(self):
        """Тест создания транзакции при завершении заказа"""
        # Добавляем позицию в заказ
        OrderItem.objects.create(
            order=self.order,
            service=self.service,
            price=Decimal('2500.00'),
            seller=self.manager
        )
        
        # Изначально транзакций нет
        self.assertEqual(Transaction.objects.count(), 0)
        
        # Завершаем заказ
        self.order.status = 'completed'
        self.order.completed_at = timezone.now()
        self.order.save()
        
        # Должны создаться транзакции
        transactions = Transaction.objects.filter(order=self.order)
        self.assertGreater(transactions.count(), 0)
        
        # Проверяем доходную транзакцию
        income_transaction = transactions.filter(type='income').first()
        self.assertIsNotNone(income_transaction)
        self.assertEqual(income_transaction.amount, self.order.total_cost)
        
        # Проверяем расходную транзакцию на себестоимость
        expense_transaction = transactions.filter(type='expense').first()
        self.assertIsNotNone(expense_transaction)
        self.assertEqual(expense_transaction.amount, self.service.cost_price)
    
    def test_no_duplicate_transactions(self):
        """Тест предотвращения дублирования транзакций"""
        # Добавляем позицию
        OrderItem.objects.create(
            order=self.order,
            service=self.service,
            price=Decimal('2500.00'),
            seller=self.manager
        )
        
        # Завершаем заказ первый раз
        self.order.status = 'completed'
        self.order.completed_at = timezone.now()
        self.order.save()
        
        initial_transactions_count = Transaction.objects.filter(order=self.order).count()
        
        # Пытаемся "завершить" заказ еще раз
        self.order.save()
        
        # Количество транзакций не должно увеличиться
        final_transactions_count = Transaction.objects.filter(order=self.order).count()
        self.assertEqual(initial_transactions_count, final_transactions_count)


class OrderAPITests(APITestCase):
    """Тесты API заказов"""
    
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
        
        self.service = Service.objects.create(
            name='API Услуга',
            cost_price=Decimal('1000.00'),
            selling_price=Decimal('2000.00'),
            category='additional'
        )
        
        self.order = Order.objects.create(
            client=self.customer,
            manager=self.manager
        )
    
    def test_order_list_api_permissions(self):
        """Тест прав доступа к API списка заказов"""
        # Неавторизованный доступ
        response = self.client.get('/api/orders/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Авторизованный доступ
        self.client.force_authenticate(user=self.manager)
        response = self.client.get('/api/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_order_create_api(self):
        """Тест создания заказа через API"""
        self.client.force_authenticate(user=self.manager)
        
        order_data = {
            'client': self.customer.pk,
            'manager': self.manager.pk,
            'status': 'new',
            'installers': [self.installer.pk]
        }
        
        response = self.client.post('/api/orders/', order_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Проверяем, что заказ создан
        order = Order.objects.get(pk=response.data['id'])
        self.assertEqual(order.client, self.customer)
        self.assertEqual(order.manager, self.manager)
    
    def test_order_update_api(self):
        """Тест обновления заказа через API"""
        self.client.force_authenticate(user=self.manager)
        
        update_data = {
            'client': self.customer.pk,
            'manager': self.manager.pk,
            'status': 'in_progress',
            'installers': [self.installer.pk]
        }
        
        response = self.client.put(f'/api/orders/{self.order.pk}/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'in_progress')


class OrderFormsTests(TestCase):
    """Тесты форм заказов"""
    
    def setUp(self):
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
            name='Форма Клиент',
            address='ул. Формовая, 123',
            phone='+7900123456',
            source='website'
        )
        
        self.service = Service.objects.create(
            name='Форма Услуга',
            cost_price=Decimal('1000.00'),
            selling_price=Decimal('2000.00'),
            category='maintenance'
        )
    
    def test_order_form_valid(self):
        """Тест валидной формы заказа"""
        form_data = {
            'client': self.customer.pk,
            'manager': self.manager.pk,
            'status': 'new',
            'installers': [self.installer.pk]
        }
        
        form = OrderForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        order = form.save()
        self.assertEqual(order.client, self.customer)
        self.assertEqual(order.manager, self.manager)
    
    def test_order_form_manager_queryset(self):
        """Тест фильтрации менеджеров в форме"""
        form = OrderForm()
        
        # Проверяем, что в queryset только менеджеры
        manager_queryset = form.fields['manager'].queryset
        for user in manager_queryset:
            self.assertEqual(user.role, 'manager')
    
    def test_order_form_installer_queryset(self):
        """Тест фильтрации монтажников в форме"""
        form = OrderForm()
        
        # Проверяем, что в queryset только монтажники
        installer_queryset = form.fields['installers'].queryset
        for user in installer_queryset:
            self.assertEqual(user.role, 'installer')
    
    def test_order_item_form_valid(self):
        """Тест валидной формы позиции заказа"""
        order = Order.objects.create(
            client=self.customer,
            manager=self.manager
        )
        
        form_data = {
            'service': self.service.pk,
            'price': '2500.00',
            'seller': self.manager.pk
        }
        
        form = OrderItemForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        item = form.save(commit=False)
        item.order = order
        item.save()
        
        self.assertEqual(item.service, self.service)
        self.assertEqual(item.price, Decimal('2500.00'))
        self.assertEqual(item.seller, self.manager)
    
    def test_order_item_form_seller_queryset(self):
        """Тест фильтрации продавцов в форме позиции"""
        form = OrderItemForm()
        
        # Проверяем, что в queryset менеджеры и монтажники
        seller_queryset = form.fields['seller'].queryset
        valid_roles = ['manager', 'installer']
        
        for user in seller_queryset:
            self.assertIn(user.role, valid_roles)


class OrderIntegrationTests(TestCase):
    """Интеграционные тесты заказов"""
    
    def setUp(self):
        self.client = Client()
        
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
            name='Интеграция Клиент',
            address='ул. Интеграционная, 123',
            phone='+7900123456',
            source='website'
        )
        
        self.service = Service.objects.create(
            name='Интеграция Услуга',
            cost_price=Decimal('1000.00'),
            selling_price=Decimal('2000.00'),
            category='installation'
        )
    
    def test_full_order_lifecycle(self):
        """Тест полного жизненного цикла заказа"""
        self.client.login(username='manager', password='testpass123')
        
        # 1. Создание заказа
        order_data = {
            'client': self.customer.pk,
            'manager': self.manager.pk,
            'status': 'new',
            'installers': [self.installer.pk]
        }
        
        response = self.client.post(reverse('order_new'), order_data)
        self.assertEqual(response.status_code, 302)
        
        order = Order.objects.get(client=self.customer)
        
        # 2. Добавление позиции
        item_data = {
            'service': self.service.pk,
            'price': '2500.00',
            'seller': self.manager.pk
        }
        
        response = self.client.post(
            reverse('order_add_item', kwargs={'pk': order.pk}),
            item_data
        )
        self.assertEqual(response.status_code, 302)
        
        # 3. Проверка обновления стоимости
        order.refresh_from_db()
        self.assertEqual(order.total_cost, Decimal('2500.00'))
        
        # 4. Изменение статуса на "в работе"
        response = self.client.post(
            reverse('order_change_status', kwargs={'pk': order.pk}),
            {'status': 'in_progress'}
        )
        self.assertEqual(response.status_code, 302)
        
        order.refresh_from_db()
        self.assertEqual(order.status, 'in_progress')
        
        # 5. Завершение заказа монтажником
        self.client.login(username='installer', password='testpass123')
        
        response = self.client.post(
            reverse('order_change_status', kwargs={'pk': order.pk}),
            {'status': 'completed'}
        )
        self.assertEqual(response.status_code, 302)
        
        order.refresh_from_db()
        self.assertEqual(order.status, 'completed')
        self.assertIsNotNone(order.completed_at)
        
        # 6. Проверка создания транзакций
        transactions = Transaction.objects.filter(order=order)
        self.assertGreater(transactions.count(), 0)
        
        income_transaction = transactions.filter(type='income').first()
        self.assertIsNotNone(income_transaction)
        self.assertEqual(income_transaction.amount, order.total_cost)
    
    def test_manager_order_isolation(self):
        """Тест изоляции заказов между менеджерами"""
        # Создаем второго менеджера
        manager2 = User.objects.create_user(
            username='manager2',
            password='testpass123',
            role='manager'
        )
        
        # Создаем заказы для разных менеджеров
        order1 = Order.objects.create(
            client=self.customer,
            manager=self.manager
        )
        
        customer2 = CustomerClient.objects.create(
            name='Клиент 2',
            address='Адрес 2',
            phone='+7900654321',
            source='avito'
        )
        
        order2 = Order.objects.create(
            client=customer2,
            manager=manager2
        )
        
        # Первый менеджер видит только свой заказ
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('order_list'))
        
        self.assertContains(response, f'Заказ #{order1.id}')
        self.assertNotContains(response, f'Заказ #{order2.id}')
        
        # Второй менеджер видит только свой заказ
        self.client.login(username='manager2', password='testpass123')
        response = self.client.get(reverse('order_list'))
        
        self.assertContains(response, f'Заказ #{order2.id}')
        self.assertNotContains(response, f'Заказ #{order1.id}')
    
    def test_installer_view_restrictions(self):
        """Тест ограничений просмотра для монтажника"""
        # Создаем заказы
        order1 = Order.objects.create(
            client=self.customer,
            manager=self.manager
        )
        order1.installers.add(self.installer)
        
        customer2 = CustomerClient.objects.create(
            name='Клиент без монтажника',
            address='Адрес без монтажника',
            phone='+7900999888',
            source='vk'
        )
        
        order2 = Order.objects.create(
            client=customer2,
            manager=self.manager
        )
        # Не назначаем монтажника на второй заказ
        
        # Монтажник видит только заказы, где он назначен
        self.client.login(username='installer', password='testpass123')
        response = self.client.get(reverse('order_list'))
        
        self.assertContains(response, f'Заказ #{order1.id}')
        self.assertNotContains(response, f'Заказ #{order2.id}')


class OrderPerformanceTests(TestCase):
    """Тесты производительности заказов"""
    
    def setUp(self):
        self.manager = User.objects.create_user(
            username='manager',
            password='testpass123',
            role='manager'
        )
        
        self.customer = CustomerClient.objects.create(
            name='Производительность Клиент',
            address='ул. Быстрая, 123',
            phone='+7900123456',
            source='website'
        )
    
    def test_bulk_order_creation(self):
        """Тест массового создания заказов"""
        orders_data = []
        
        # Создаем данные для 50 заказов
        for i in range(50):
            orders_data.append(Order(
                client=self.customer,
                manager=self.manager,
                status='new'
            ))
        
        # Массовое создание
        orders = Order.objects.bulk_create(orders_data)
        
        self.assertEqual(len(orders), 50)
        self.assertEqual(Order.objects.count(), 50)
    
    def test_order_list_query_optimization(self):
        """Тест оптимизации запросов списка заказов"""
        # Создаем несколько заказов
        for i in range(10):
            Order.objects.create(
                client=self.customer,
                manager=self.manager
            )
        
        # Проверяем количество запросов при получении списка с select_related
        with self.assertNumQueries(1):
            orders = list(Order.objects.select_related('client', 'manager').all())
            
        self.assertEqual(len(orders), 10)


class OrderValidationTests(TestCase):
    """Тесты валидации заказов"""
    
    def setUp(self):
        self.manager = User.objects.create_user(
            username='manager',
            password='testpass123',
            role='manager'
        )
        
        self.customer = CustomerClient.objects.create(
            name='Валидация Клиент',
            address='ул. Валидационная, 123',
            phone='+7900123456',
            source='website'
        )
    
    def test_order_manager_role_validation(self):
        """Тест валидации роли менеджера"""
        # Создаем пользователя не-менеджера
        installer = User.objects.create_user(
            username='installer',
            password='testpass123',
            role='installer'
        )
        
        # В текущей модели нет валидации роли менеджера
        # Но можно создать заказ с монтажником как менеджером
        order = Order.objects.create(
            client=self.customer,
            manager=installer  # Технически возможно
        )
        
        # В реальном проекте здесь должна быть валидация
        self.assertEqual(order.manager.role, 'installer')
    
    def test_order_total_cost_calculation(self):
        """Тест расчета общей стоимости заказа"""
        order = Order.objects.create(
            client=self.customer,
            manager=self.manager
        )
        
        # Создаем услуги
        service1 = Service.objects.create(
            name='Услуга 1',
            cost_price=Decimal('1000.00'),
            selling_price=Decimal('2000.00'),
            category='installation'
        )
        
        service2 = Service.objects.create(
            name='Услуга 2',
            cost_price=Decimal('500.00'),
            selling_price=Decimal('1000.00'),
            category='maintenance'
        )
        
        # Добавляем позиции
        OrderItem.objects.create(
            order=order,
            service=service1,
            price=Decimal('2500.00'),
            seller=self.manager
        )
        
        OrderItem.objects.create(
            order=order,
            service=service2,
            price=Decimal('1500.00'),
            seller=self.manager
        )
        
        order.refresh_from_db()
        expected_total = Decimal('2500.00') + Decimal('1500.00')
        self.assertEqual(order.total_cost, expected_total)