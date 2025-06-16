# finance/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta
from .models import Transaction, SalaryPayment
from .forms import TransactionForm, SalaryPaymentForm
from .utils import calculate_installer_salary, calculate_manager_salary, calculate_owner_salary
from customer_clients.models import Client as CustomerClient
from services.models import Service
from orders.models import Order, OrderItem

User = get_user_model()


class TransactionModelTests(TestCase):
    """Тесты модели Transaction"""
    
    def setUp(self):
        self.manager = User.objects.create_user(
            username='manager',
            password='testpass123',
            role='manager'
        )
        
        self.customer = CustomerClient.objects.create(
            name='Финанс Клиент',
            address='ул. Финансовая, 123',
            phone='+7900123456',
            source='website'
        )
        
        self.order = Order.objects.create(
            client=self.customer,
            manager=self.manager,
            total_cost=Decimal('10000.00')
        )
    
    def test_create_income_transaction(self):
        """Тест создания доходной транзакции"""
        transaction = Transaction.objects.create(
            type='income',
            amount=Decimal('10000.00'),
            description='Доход от заказа',
            order=self.order
        )
        
        self.assertEqual(transaction.type, 'income')
        self.assertEqual(transaction.amount, Decimal('10000.00'))
        self.assertEqual(transaction.order, self.order)
        self.assertEqual(str(transaction), 'Доход - 10000.00')
    
    def test_create_expense_transaction(self):
        """Тест создания расходной транзакции"""
        transaction = Transaction.objects.create(
            type='expense',
            amount=Decimal('5000.00'),
            description='Себестоимость услуг',
            order=self.order
        )
        
        self.assertEqual(transaction.type, 'expense')
        self.assertEqual(transaction.amount, Decimal('5000.00'))
        self.assertEqual(str(transaction), 'Расход - 5000.00')
    
    def test_company_balance_calculation(self):
        """Тест расчета баланса компании"""
        # Создаем несколько транзакций
        Transaction.objects.create(
            type='income',
            amount=Decimal('10000.00'),
            description='Доход 1'
        )
        
        Transaction.objects.create(
            type='income',
            amount=Decimal('15000.00'),
            description='Доход 2'
        )
        
        Transaction.objects.create(
            type='expense',
            amount=Decimal('8000.00'),
            description='Расход 1'
        )
        
        Transaction.objects.create(
            type='expense',
            amount=Decimal('3000.00'),
            description='Расход 2'
        )
        
        # Баланс = (10000 + 15000) - (8000 + 3000) = 14000
        balance = Transaction.get_company_balance()
        self.assertEqual(balance, Decimal('14000.00'))
    
    def test_company_balance_empty(self):
        """Тест баланса при отсутствии транзакций"""
        balance = Transaction.get_company_balance()
        self.assertEqual(balance, Decimal('0.00'))


class SalaryPaymentModelTests(TestCase):
    """Тесты модели SalaryPayment"""
    
    def setUp(self):
        self.installer = User.objects.create_user(
            username='installer',
            password='testpass123',
            role='installer',
            first_name='Иван',
            last_name='Монтажников'
        )
    
    def test_create_salary_payment(self):
        """Тест создания выплаты зарплаты"""
        payment = SalaryPayment.objects.create(
            user=self.installer,
            amount=Decimal('50000.00'),
            period_start=datetime(2025, 6, 1).date(),
            period_end=datetime(2025, 6, 30).date()
        )
        
        self.assertEqual(payment.user, self.installer)
        self.assertEqual(payment.amount, Decimal('50000.00'))
        self.assertEqual(str(payment), 'ЗП для Иван Монтажников - 50000.00')
    
    def test_salary_payment_verbose_names(self):
        """Тест verbose_name модели выплат"""
        self.assertEqual(SalaryPayment._meta.verbose_name, 'Выплата зарплаты')
        self.assertEqual(SalaryPayment._meta.verbose_name_plural, 'Выплаты зарплат')


class FinanceViewsTests(TestCase):
    """Тесты представлений финансов"""
    
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
        
        # Создаем тестовые транзакции
        Transaction.objects.create(
            type='income',
            amount=Decimal('20000.00'),
            description='Тестовый доход'
        )
        
        Transaction.objects.create(
            type='expense',
            amount=Decimal('5000.00'),
            description='Тестовый расход'
        )
    
    def test_finance_dashboard_owner_only(self):
        """Тест доступа к финансовому дашборду только для владельца"""
        # Менеджер не должен иметь доступ
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('finance_dashboard'))
        self.assertRedirects(response, reverse('dashboard'))
        
        # Владелец должен иметь доступ
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('finance_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Проверяем наличие данных баланса
        self.assertContains(response, '15000.00')  # Баланс = 20000 - 5000
    
    def test_transaction_list_owner_only(self):
        """Тест доступа к списку транзакций только для владельца"""
        # Менеджер не должен иметь доступ
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('transaction_list'))
        self.assertRedirects(response, reverse('dashboard'))
        
        # Владелец должен иметь доступ
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('transaction_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Тестовый доход')
        self.assertContains(response, 'Тестовый расход')
    
    def test_transaction_list_filter(self):
        """Тест фильтрации транзакций по типу"""
        self.client.login(username='owner', password='testpass123')
        
        # Фильтр по доходам
        response = self.client.get(reverse('transaction_list') + '?type=income')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Тестовый доход')
        self.assertNotContains(response, 'Тестовый расход')
        
        # Фильтр по расходам
        response = self.client.get(reverse('transaction_list') + '?type=expense')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Тестовый расход')
        self.assertNotContains(response, 'Тестовый доход')
    
    def test_transaction_new_owner_only(self):
        """Тест создания транзакции только для владельца"""
        # Менеджер не должен создавать транзакции
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('transaction_new'))
        self.assertRedirects(response, reverse('dashboard'))
        
        # Владелец должен создавать транзакции
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('transaction_new'))
        self.assertEqual(response.status_code, 200)
    
    def test_transaction_create_post(self):
        """Тест создания транзакции через POST"""
        self.client.login(username='owner', password='testpass123')
        
        transaction_data = {
            'type': 'expense',
            'amount': '7500.00',
            'description': 'Новый расход'
        }
        
        response = self.client.post(reverse('transaction_new'), transaction_data)
        self.assertEqual(response.status_code, 302)  # Редирект после создания
        
        # Проверяем, что транзакция создана
        transaction = Transaction.objects.get(description='Новый расход')
        self.assertEqual(transaction.amount, Decimal('7500.00'))
        self.assertEqual(transaction.type, 'expense')
    
    def test_salary_calculation_view(self):
        """Тест страницы расчета зарплат"""
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('salary_calculation'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Расчет зарплат')
        
        # Проверяем наличие пользователей в контексте
        users = response.context['users']
        self.assertIn(self.manager, users)
        self.assertIn(self.installer, users)
    
    def test_create_salary_payment_view(self):
        """Тест создания выплаты зарплаты"""
        self.client.login(username='owner', password='testpass123')
        
        payment_data = {
            'amount': '45000.00',
            'period_start': '2025-06-01',
            'period_end': '2025-06-30'
        }
        
        response = self.client.post(
            reverse('create_salary_payment', kwargs={'user_id': self.installer.pk}),
            payment_data
        )
        
        self.assertEqual(response.status_code, 302)  # Редирект после создания
        
        # Проверяем, что выплата создана
        payment = SalaryPayment.objects.get(user=self.installer)
        self.assertEqual(payment.amount, Decimal('45000.00'))
        
        # Проверяем, что создана соответствующая транзакция расхода
        expense_transaction = Transaction.objects.filter(
            type='expense',
            description__contains='Выплата зарплаты'
        ).first()
        self.assertIsNotNone(expense_transaction)
        self.assertEqual(expense_transaction.amount, Decimal('45000.00'))


class SalaryCalculationTests(TestCase):
    """Тесты расчета зарплат"""
    
    def setUp(self):
        # Создаем пользователей
        self.manager = User.objects.create_user(
            username='manager',
            password='testpass123',
            role='manager',
            first_name='Иван',
            last_name='Менеджеров'
        )
        
        self.installer = User.objects.create_user(
            username='installer',
            password='testpass123',
            role='installer',
            first_name='Петр',
            last_name='Монтажников'
        )
        
        # Создаем клиента
        self.customer = CustomerClient.objects.create(
            name='Зарплата Клиент',
            address='ул. Зарплатная, 123',
            phone='+7900123456',
            source='website'
        )
        
        # Создаем услуги
        self.conditioner = Service.objects.create(
            name='Кондиционер Samsung',
            cost_price=Decimal('20000.00'),
            selling_price=Decimal('35000.00'),
            category='conditioner'
        )
        
        self.installation = Service.objects.create(
            name='Монтаж кондиционера',
            cost_price=Decimal('2000.00'),
            selling_price=Decimal('5000.00'),
            category='installation'
        )
        
        self.additional = Service.objects.create(
            name='Чистка фильтров',
            cost_price=Decimal('500.00'),
            selling_price=Decimal('2000.00'),
            category='additional'
        )
        
        # Создаем завершенный заказ
        self.order = Order.objects.create(
            client=self.customer,
            manager=self.manager,
            status='completed',
            completed_at=timezone.now()
        )
        self.order.installers.add(self.installer)
        
        # Добавляем позиции в заказ
        OrderItem.objects.create(
            order=self.order,
            service=self.conditioner,
            price=Decimal('35000.00'),
            seller=self.manager
        )
        
        OrderItem.objects.create(
            order=self.order,
            service=self.installation,
            price=Decimal('5000.00'),
            seller=self.manager
        )
        
        OrderItem.objects.create(
            order=self.order,
            service=self.additional,
            price=Decimal('2000.00'),
            seller=self.installer
        )
    
    def test_calculate_installer_salary(self):
        """Тест расчета зарплаты монтажника"""
        start_date = timezone.now() - timedelta(days=30)
        end_date = timezone.now()
        
        salary_data = calculate_installer_salary(self.installer, start_date, end_date)
        
        # Проверяем структуру результата
        self.assertIn('installation_pay', salary_data)
        self.assertIn('additional_pay', salary_data)
        self.assertIn('total_salary', salary_data)
        self.assertIn('completed_orders_count', salary_data)
        
        # Проверяем расчеты
        self.assertEqual(salary_data['completed_orders_count'], 1)
        self.assertEqual(salary_data['installation_pay'], Decimal('1500.00'))  # 1500 за монтаж
        
        # Проверяем оплату за дополнительные услуги (30% от прибыли)
        additional_profit = Decimal('2000.00') - Decimal('500.00')  # 1500
        expected_additional_pay = additional_profit * Decimal('0.3')  # 450
        self.assertEqual(salary_data['additional_pay'], expected_additional_pay)
    
    def test_calculate_manager_salary(self):
        """Тест расчета зарплаты менеджера"""
        start_date = timezone.now() - timedelta(days=30)
        end_date = timezone.now()
        
        salary_data = calculate_manager_salary(self.manager, start_date, end_date)
        
        # Проверяем структуру результата
        self.assertIn('fixed_salary', salary_data)
        self.assertIn('orders_pay', salary_data)
        self.assertIn('conditioner_pay', salary_data)
        self.assertIn('total_salary', salary_data)
        
        # Проверяем расчеты
        self.assertEqual(salary_data['fixed_salary'], Decimal('30000.00'))
        self.assertEqual(salary_data['orders_pay'], Decimal('250.00'))  # 250 за заказ
        
        # Проверяем оплату за кондиционеры (20% от прибыли)
        conditioner_profit = Decimal('35000.00') - Decimal('20000.00')  # 15000
        expected_conditioner_pay = conditioner_profit * Decimal('0.2')  # 3000
        self.assertEqual(salary_data['conditioner_pay'], expected_conditioner_pay)
    
    def test_calculate_owner_salary(self):
        """Тест расчета зарплаты владельца"""
        start_date = timezone.now() - timedelta(days=30)
        end_date = timezone.now()
        
        salary_data = calculate_owner_salary(start_date, end_date)
        
        # Проверяем структуру результата
        self.assertIn('installation_pay', salary_data)
        self.assertIn('total_revenue', salary_data)
        self.assertIn('total_cost_price', salary_data)
        self.assertIn('remaining_profit', salary_data)
        self.assertIn('total_salary', salary_data)
        
        # Проверяем расчеты
        self.assertEqual(salary_data['installation_pay'], Decimal('1500.00'))  # 1500 за монтаж
        self.assertEqual(salary_data['total_revenue'], Decimal('42000.00'))  # Сумма всех позиций
        
        # Общая себестоимость
        expected_cost_price = (
            Decimal('20000.00') +  # кондиционер
            Decimal('2000.00') +   # монтаж
            Decimal('500.00')      # дополнительная услуга
        )
        self.assertEqual(salary_data['total_cost_price'], expected_cost_price)


class FinanceAPITests(APITestCase):
    """Тесты API финансов"""
    
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
        
        self.transaction = Transaction.objects.create(
            type='income',
            amount=Decimal('15000.00'),
            description='API Тестовая транзакция'
        )
    
    def test_transaction_api_owner_only(self):
        """Тест доступа к API транзакций только для владельца"""
        # Неавторизованный доступ
        response = self.client.get('/api/transactions/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Менеджер не должен иметь доступ
        self.client.force_authenticate(user=self.manager)
        response = self.client.get('/api/transactions/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Владелец должен иметь доступ
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/transactions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_transaction_create_api(self):
        """Тест создания транзакции через API"""
        self.client.force_authenticate(user=self.owner)
        
        transaction_data = {
            'type': 'expense',
            'amount': '8000.00',
            'description': 'API Новая транзакция'
        }
        
        response = self.client.post('/api/transactions/', transaction_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Проверяем, что транзакция создана
        transaction = Transaction.objects.get(description='API Новая транзакция')
        self.assertEqual(transaction.amount, Decimal('8000.00'))
        self.assertEqual(transaction.type, 'expense')
    
    def test_transaction_filter_api(self):
        """Тест фильтрации транзакций через API"""
        # Создаем дополнительную транзакцию
        Transaction.objects.create(
            type='expense',
            amount=Decimal('5000.00'),
            description='API Расходная транзакция'
        )
        
        self.client.force_authenticate(user=self.owner)
        
        # Фильтр по типу
        response = self.client.get('/api/transactions/?type=income')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['type'], 'income')
    
    def test_finance_balance_api(self):
        """Тест API баланса компании"""
        # Создаем несколько транзакций
        Transaction.objects.create(
            type='expense',
            amount=Decimal('3000.00'),
            description='Тестовый расход'
        )
        
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/finance/balance/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Баланс = 15000 (из setup) - 3000 = 12000
        self.assertEqual(response.data['balance'], 12000.0)
    
    def test_salary_calculation_api(self):
        """Тест API расчета зарплаты"""
        installer = User.objects.create_user(
            username='installer',
            password='testpass123',
            role='installer'
        )
        
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f'/api/finance/calculate-salary/{installer.pk}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('salary', response.data)


class FinanceFormsTests(TestCase):
    """Тесты форм финансов"""
    
    def setUp(self):
        self.manager = User.objects.create_user(
            username='manager',
            password='testpass123',
            role='manager'
        )
        
        self.customer = CustomerClient.objects.create(
            name='Форма Клиент',
            address='ул. Формовая, 123',
            phone='+7900123456',
            source='website'
        )
        
        self.order = Order.objects.create(
            client=self.customer,
            manager=self.manager
        )
    
    def test_transaction_form_valid(self):
        """Тест валидной формы транзакции"""
        form_data = {
            'type': 'income',
            'amount': '12000.00',
            'description': 'Тестовая транзакция',
            'order': self.order.pk
        }
        
        form = TransactionForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        transaction = form.save()
        self.assertEqual(transaction.amount, Decimal('12000.00'))
        self.assertEqual(transaction.type, 'income')
        self.assertEqual(transaction.order, self.order)
    
    def test_transaction_form_required_fields(self):
        """Тест обязательных полей формы транзакции"""
        form_data = {}
        form = TransactionForm(data=form_data)
        self.assertFalse(form.is_valid())
        
        required_fields = ['type', 'amount', 'description']
        for field in required_fields:
            self.assertIn(field, form.errors)
    
    def test_salary_payment_form_valid(self):
        """Тест валидной формы выплаты зарплаты"""
        form_data = {
            'amount': '50000.00',
            'period_start': '2025-06-01',
            'period_end': '2025-06-30'
        }
        
        form = SalaryPaymentForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        payment = form.save(commit=False)
        payment.user = self.manager
        payment.save()
        
        self.assertEqual(payment.amount, Decimal('50000.00'))
        self.assertEqual(payment.user, self.manager)


class FinanceIntegrationTests(TestCase):
    """Интеграционные тесты финансов"""
    
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
        
        self.installer = User.objects.create_user(
            username='installer',
            password='testpass123',
            role='installer'
        )
    
    def test_full_finance_workflow(self):
        """Тест полного финансового рабочего процесса"""
        self.client.login(username='owner', password='testpass123')
        
        # 1. Создание доходной транзакции
        income_data = {
            'type': 'income',
            'amount': '25000.00',
            'description': 'Доход от продаж'
        }
        
        response = self.client.post(reverse('transaction_new'), income_data)
        self.assertEqual(response.status_code, 302)
        
        # 2. Создание расходной транзакции
        expense_data = {
            'type': 'expense',
            'amount': '8000.00',
            'description': 'Операционные расходы'
        }
        
        response = self.client.post(reverse('transaction_new'), expense_data)
        self.assertEqual(response.status_code, 302)
        
        # 3. Проверка баланса на дашборде
        response = self.client.get(reverse('finance_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Баланс должен быть 25000 - 8000 = 17000
        self.assertContains(response, '17000.00')
        
        # 4. Создание выплаты зарплаты
        payment_data = {
            'amount': '45000.00',
            'period_start': '2025-06-01',
            'period_end': '2025-06-30'
        }
        
        response = self.client.post(
            reverse('create_salary_payment', kwargs={'user_id': self.installer.pk}),
            payment_data
        )
        self.assertEqual(response.status_code, 302)
        
        # 5. Проверка, что создалась соответствующая расходная транзакция
        salary_transaction = Transaction.objects.filter(
            type='expense',
            description__contains='Выплата зарплаты'
        ).first()
        
        self.assertIsNotNone(salary_transaction)
        self.assertEqual(salary_transaction.amount, Decimal('45000.00'))
        
        # 6. Итоговый баланс должен быть 17000 - 45000 = -28000
        final_balance = Transaction.get_company_balance()
        self.assertEqual(final_balance, Decimal('-28000.00'))
    
    def test_salary_calculation_integration(self):
        """Тест интеграции расчета зарплат"""
        # Создаем тестовые данные для расчета зарплат
        customer = CustomerClient.objects.create(
            name='Интеграция Клиент',
            address='ул. Интеграционная, 123',
            phone='+7900123456',
            source='website'
        )
        
        service = Service.objects.create(
            name='Интеграция Услуга',
            cost_price=Decimal('10000.00'),
            selling_price=Decimal('18000.00'),
            category='conditioner'
        )
        
        order = Order.objects.create(
            client=customer,
            manager=self.manager,
            status='completed',
            completed_at=timezone.now()
        )
        order.installers.add(self.installer)
        
        OrderItem.objects.create(
            order=order,
            service=service,
            price=Decimal('18000.00'),
            seller=self.manager
        )
        
        self.client.login(username='owner', password='testpass123')
        
        # Проверяем страницу расчета зарплат
        response = self.client.get(reverse('salary_calculation'))
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что в расчетах есть данные
        calculations = response.context['salary_calculations']
        self.assertGreater(len(calculations), 0)
        
        # Находим расчет для менеджера
        manager_calculation = None
        for calc in calculations:
            if calc['user'] == self.manager:
                manager_calculation = calc['calculation']
                break
        
        self.assertIsNotNone(manager_calculation)
        self.assertIn('total_salary', manager_calculation)
        self.assertGreater(manager_calculation['total_salary'], Decimal('30000.00'))  # Больше базовой зарплаты


class FinanceSecurityTests(TestCase):
    """Тесты безопасности финансов"""
    
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
        
        self.installer = User.objects.create_user(
            username='installer',
            password='testpass123',
            role='installer'
        )
    
    def test_finance_access_control(self):
        """Тест контроля доступа к финансовым функциям"""
        finance_urls = [
            reverse('finance_dashboard'),
            reverse('transaction_list'),
            reverse('transaction_new'),
            reverse('salary_calculation'),
        ]
        
        # Неавторизованный доступ - должен редиректить на логин
        for url in finance_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/user_accounts/login/', response.url)
        
        # Менеджер не должен иметь доступа к финансам
        self.client.login(username='manager', password='testpass123')
        for url in finance_urls:
            response = self.client.get(url)
            if response.status_code != 302:  # Если не редирект
                self.assertEqual(response.status_code, 403)  # То должен быть запрет
        
        # Монтажник не должен иметь доступа к финансам
        self.client.login(username='installer', password='testpass123')
        for url in finance_urls:
            response = self.client.get(url)
            if response.status_code != 302:  # Если не редирект
                self.assertEqual(response.status_code, 403)  # То должен быть запрет
        
        # Владелец должен иметь полный доступ
        self.client.login(username='owner', password='testpass123')
        for url in finance_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
    
    def test_salary_payment_access_control(self):
        """Тест контроля доступа к выплатам зарплат"""
        # Только владелец может создавать выплаты
        url = reverse('create_salary_payment', kwargs={'user_id': self.installer.pk})
        
        # Менеджер не должен создавать выплаты
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Редирект
        
        # Владелец должен создавать выплаты
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class FinancePerformanceTests(TestCase):
    """Тесты производительности финансов"""
    
    def test_balance_calculation_performance(self):
        """Тест производительности расчета баланса"""
        # Создаем много транзакций
        transactions = []
        for i in range(1000):
            transactions.append(Transaction(
                type='income' if i % 2 == 0 else 'expense',
                amount=Decimal(f'{1000 + i}.00'),
                description=f'Транзакция {i}'
            ))
        
        Transaction.objects.bulk_create(transactions)
        
        # Проверяем, что расчет баланса выполняется быстро
        import time
        start_time = time.time()
        
        balance = Transaction.get_company_balance()
        
        end_time = time.time()
        calculation_time = end_time - start_time
        
        # Расчет должен выполниться менее чем за 1 секунду
        self.assertLess(calculation_time, 1.0)
        self.assertIsInstance(balance, Decimal)
    
    def test_salary_calculation_performance(self):
        """Тест производительности расчета зарплат"""
        # Создаем тестовые данные
        manager = User.objects.create_user(
            username='perf_manager',
            password='testpass123',
            role='manager'
        )
        
        # Засекаем время расчета зарплаты
        import time
        start_time = time.time()
        
        salary_data = calculate_manager_salary(manager)
        
        end_time = time.time()
        calculation_time = end_time - start_time
        
        # Расчет должен выполниться быстро
        self.assertLess(calculation_time, 0.5)
        self.assertIsInstance(salary_data, dict)