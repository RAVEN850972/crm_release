# user_accounts/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
import json

User = get_user_model()


class UserModelTests(TestCase):
    """Тесты модели User"""
    
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'role': 'manager',
            'phone': '+7900123456'
        }
    
    def test_create_user(self):
        """Тест создания пользователя"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.role, 'manager')
        self.assertTrue(user.check_password('testpass123'))
        self.assertEqual(str(user), 'Test User - Менеджер')
    
    def test_user_roles(self):
        """Тест ролей пользователей"""
        roles = ['owner', 'manager', 'installer']
        for role in roles:
            user = User.objects.create_user(
                username=f'user_{role}',
                password='testpass123',
                role=role
            )
            self.assertEqual(user.role, role)
    
    def test_user_get_full_name(self):
        """Тест получения полного имени"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.get_full_name(), 'Test User')
        
        # Если нет имени и фамилии
        user_no_name = User.objects.create_user(
            username='noname',
            password='testpass123',
            role='manager'
        )
        self.assertEqual(user_no_name.get_full_name(), '')


class UserViewsTests(TestCase):
    """Тесты представлений пользователей"""
    
    def setUp(self):
        self.client = Client()
        
        # Создаем пользователей разных ролей
        self.owner = User.objects.create_user(
            username='owner',
            password='testpass123',
            role='owner',
            first_name='Owner',
            last_name='User'
        )
        
        self.manager = User.objects.create_user(
            username='manager',
            password='testpass123',
            role='manager',
            first_name='Manager',
            last_name='User'
        )
        
        self.installer = User.objects.create_user(
            username='installer',
            password='testpass123',
            role='installer',
            first_name='Installer',
            last_name='User'
        )
    
    def test_login_view_get(self):
        """Тест GET запроса к странице входа"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'username')
        self.assertContains(response, 'password')
    
    def test_login_view_post_success(self):
        """Тест успешного входа"""
        response = self.client.post(reverse('login'), {
            'username': 'owner',
            'password': 'testpass123'
        })
        self.assertRedirects(response, '/')
    
    def test_login_view_post_failure(self):
        """Тест неуспешного входа"""
        response = self.client.post(reverse('login'), {
            'username': 'owner',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Неверное имя пользователя или пароль')
    
    def test_login_ajax_success(self):
        """Тест AJAX входа"""
        response = self.client.post(
            reverse('login'),
            json.dumps({
                'username': 'owner',
                'password': 'testpass123'
            }),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['username'], 'owner')
        self.assertEqual(data['user']['role'], 'owner')
    
    def test_profile_view_requires_login(self):
        """Тест доступа к профилю без авторизации"""
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, '/user_accounts/login/?next=/user_accounts/profile/')
    
    def test_profile_view_authenticated(self):
        """Тест доступа к профилю с авторизацией"""
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Manager User')
    
    def test_user_list_owner_only(self):
        """Тест списка пользователей - только для владельца"""
        # Менеджер не должен иметь доступ
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('user_list'))
        self.assertRedirects(response, reverse('dashboard'))
        
        # Владелец должен иметь доступ
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'manager')
        self.assertContains(response, 'installer')
    
    def test_user_creation_owner_only(self):
        """Тест создания пользователей - только для владельца"""
        # Менеджер не должен создавать пользователей
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('user_new'))
        self.assertRedirects(response, reverse('dashboard'))
        
        # Владелец должен создавать пользователей
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('user_new'))
        self.assertEqual(response.status_code, 200)
        
        # Создание нового пользователя
        response = self.client.post(reverse('user_new'), {
            'username': 'newuser',
            'password1': 'newpass123',
            'password2': 'newpass123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'manager',
            'email': 'new@example.com'
        })
        
        # Должен быть редирект после создания
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что пользователь создан
        self.assertTrue(User.objects.filter(username='newuser').exists())


class UserAPITests(APITestCase):
    """Тесты API пользователей"""
    
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
    
    def test_user_list_owner(self):
        """Тест списка пользователей для владельца"""
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/users/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)  # все пользователи
    
    def test_user_list_manager(self):
        """Тест списка пользователей для менеджера"""
        self.client.force_authenticate(user=self.manager)
        response = self.client.get('/api/users/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Менеджер видит только монтажников и себя
        usernames = [user['username'] for user in response.data['results']]
        self.assertIn('manager', usernames)
        self.assertIn('installer', usernames)
        self.assertNotIn('owner', usernames)
    
    def test_user_list_installer(self):
        """Тест списка пользователей для монтажника"""
        self.client.force_authenticate(user=self.installer)
        response = self.client.get('/api/users/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Монтажник видит только себя
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'installer')
    
    def test_user_filter_by_role(self):
        """Тест фильтрации пользователей по роли"""
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/users/?role=manager')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['role'], 'manager')
    
    def test_user_search(self):
        """Тест поиска пользователей"""
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/users/?search=manager')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'manager')


class UserPermissionsTests(TestCase):
    """Тесты прав доступа"""
    
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
    
    def test_owner_permissions(self):
        """Тест прав владельца"""
        self.client.login(username='owner', password='testpass123')
        
        # Владелец имеет доступ ко всем функциям пользователей
        urls = [
            reverse('user_list'),
            reverse('user_new'),
            reverse('user_detail', kwargs={'pk': self.manager.pk}),
            reverse('user_edit', kwargs={'pk': self.manager.pk}),
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 403, f"URL {url} should be accessible for owner")
    
    def test_manager_permissions(self):
        """Тест прав менеджера"""
        self.client.login(username='manager', password='testpass123')
        
        # Менеджер НЕ имеет доступа к управлению пользователями
        restricted_urls = [
            reverse('user_list'),
            reverse('user_new'),
            reverse('user_detail', kwargs={'pk': self.installer.pk}),
            reverse('user_edit', kwargs={'pk': self.installer.pk}),
        ]
        
        for url in restricted_urls:
            response = self.client.get(url)
            # Должен быть редирект, а не доступ
            self.assertEqual(response.status_code, 302, f"URL {url} should redirect for manager")
    
    def test_installer_permissions(self):
        """Тест прав монтажника"""
        self.client.login(username='installer', password='testpass123')
        
        # Монтажник НЕ имеет доступа к управлению пользователями
        restricted_urls = [
            reverse('user_list'),
            reverse('user_new'),
            reverse('user_detail', kwargs={'pk': self.manager.pk}),
            reverse('user_edit', kwargs={'pk': self.manager.pk}),
        ]
        
        for url in restricted_urls:
            response = self.client.get(url)
            # Должен быть редирект, а не доступ
            self.assertEqual(response.status_code, 302, f"URL {url} should redirect for installer")


class UserFormsTests(TestCase):
    """Тесты форм пользователей"""
    
    def test_user_creation_form_valid(self):
        """Тест валидной формы создания пользователя"""
        from user_accounts.forms import CustomUserCreationForm
        
        form_data = {
            'username': 'testuser',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'role': 'manager',
            'phone': '+7900123456'
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        user = form.save()
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.role, 'manager')
    
    def test_user_creation_form_invalid(self):
        """Тест невалидной формы создания пользователя"""
        from user_accounts.forms import CustomUserCreationForm
        
        # Пароли не совпадают
        form_data = {
            'username': 'testuser',
            'password1': 'testpass123',
            'password2': 'differentpass',
            'role': 'manager'
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
    
    def test_profile_form(self):
        """Тест формы профиля"""
        from user_accounts.forms import ProfileForm
        
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='manager'
        )
        
        form_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
            'phone': '+7900654321'
        }
        
        form = ProfileForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())
        
        updated_user = form.save()
        self.assertEqual(updated_user.first_name, 'Updated')
        self.assertEqual(updated_user.email, 'updated@example.com')


class UserIntegrationTests(TestCase):
    """Интеграционные тесты"""
    
    def setUp(self):
        self.client = Client()
        
        self.owner = User.objects.create_user(
            username='owner',
            password='testpass123',
            role='owner'
        )
    
    def test_full_user_lifecycle(self):
        """Тест полного жизненного цикла пользователя"""
        self.client.login(username='owner', password='testpass123')
        
        # 1. Создание пользователя
        response = self.client.post(reverse('user_new'), {
            'username': 'lifecycle_user',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Lifecycle',
            'last_name': 'User',
            'role': 'manager',
            'email': 'lifecycle@example.com'
        })
        
        user = User.objects.get(username='lifecycle_user')
        self.assertEqual(user.role, 'manager')
        
        # 2. Просмотр пользователя
        response = self.client.get(reverse('user_detail', kwargs={'pk': user.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lifecycle User')
        
        # 3. Редактирование пользователя
        response = self.client.post(reverse('user_edit', kwargs={'pk': user.pk}), {
            'first_name': 'Updated',
            'last_name': 'User',
            'email': 'updated@example.com',
            'role': 'installer',  # Изменяем роль
            'phone': '+7900123456'
        })
        
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Updated')
        self.assertEqual(user.role, 'installer')
        
        # 4. Проверка входа созданного пользователя
        self.client.logout()
        login_response = self.client.post(reverse('login'), {
            'username': 'lifecycle_user',
            'password': 'testpass123'
        })
        self.assertRedirects(login_response, '/')
    
    def test_user_role_based_navigation(self):
        """Тест навигации в зависимости от роли"""
        # Создаем пользователей разных ролей
        manager = User.objects.create_user(
            username='test_manager',
            password='testpass123',
            role='manager'
        )
        
        installer = User.objects.create_user(
            username='test_installer',
            password='testpass123',
            role='installer'
        )
        
        # Проверяем доступ менеджера
        self.client.login(username='test_manager', password='testpass123')
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 302)  # Редирект
        
        # Проверяем доступ монтажника
        self.client.login(username='test_installer', password='testpass123')
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 302)  # Редирект
        
        # Проверяем доступ владельца
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 200)  # Доступ разрешен