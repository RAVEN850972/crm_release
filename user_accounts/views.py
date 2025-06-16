from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User
from .forms import CustomUserCreationForm, CustomUserChangeForm, ProfileForm
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from django.contrib.auth import authenticate, login


@ensure_csrf_cookie
def login_view(request):
    """
    Представление для авторизации пользователей.
    Поддерживает как обычные POST-запросы, так и AJAX.
    """
    if request.method == 'POST':
        # Проверяем, это AJAX запрос или обычная форма
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if is_ajax:
            try:
                # Для AJAX запросов используем JSON
                content_type = request.content_type
                if content_type == 'application/json':
                    data = json.loads(request.body)
                    username = data.get('username', '')
                    password = data.get('password', '')
                else:
                    # Если Content-Type не JSON, берем из POST
                    username = request.POST.get('username', '')
                    password = request.POST.get('password', '')
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse({'success': False, 'error': 'Неверный формат данных'}, status=400)
        else:
            # Для обычных форм используем POST
            username = request.POST.get('username', '')
            password = request.POST.get('password', '')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'redirect': '/',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'full_name': user.get_full_name(),
                        'role': user.role
                    }
                })
            else:
                return redirect('dashboard')
        else:
            error_message = 'Неверное имя пользователя или пароль'
            
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': error_message
                }, status=400)
            else:
                messages.error(request, error_message)
                return render(request, 'user_accounts/login.html')
    
    return render(request, 'user_accounts/login.html')

@login_required
def profile(request):
    """Страница профиля пользователя с расчетом зарплаты"""
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    
    # Расчет зарплаты для текущего пользователя
    salary_data = None
    period_start = None
    period_end = None
    
    if request.user.role in ['installer', 'manager', 'owner']:
        # Период по умолчанию - текущий месяц
        today = timezone.now()
        period_start = today.replace(day=1)
        period_end = today
        
        # Можно передать параметры периода через GET
        start_date_param = request.GET.get('start_date')
        end_date_param = request.GET.get('end_date')
        
        if start_date_param and end_date_param:
            try:
                period_start = datetime.strptime(start_date_param, '%Y-%m-%d')
                period_end = datetime.strptime(end_date_param, '%Y-%m-%d')
            except ValueError:
                pass
        
        # Импортируем функции расчета зарплаты, если доступны
        try:
            from finance.utils import calculate_installer_salary, calculate_manager_salary, calculate_owner_salary
            
            if request.user.role == 'installer':
                salary_data = calculate_installer_salary(request.user, period_start, period_end)
            elif request.user.role == 'manager':
                salary_data = calculate_manager_salary(request.user, period_start, period_end)
            elif request.user.role == 'owner':
                salary_data = calculate_owner_salary(period_start, period_end)
        except ImportError:
            # Функции расчета зарплаты недоступны
            pass
    
    context = {
        'form': form,
        'salary_data': salary_data,
        'period_start': period_start,
        'period_end': period_end,
        'can_view_salary': request.user.role in ['installer', 'manager', 'owner'],
    }
    
    return render(request, 'user_accounts/profile.html', context)

@login_required
def user_list(request):
    """Список пользователей - ТОЛЬКО для владельца"""
    if request.user.role != 'owner':
        messages.error(request, 'У вас нет прав для просмотра списка пользователей.')
        return redirect('dashboard')
    
    # Получаем параметры фильтрации
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    sort_by = request.GET.get('sort', '-date_joined')
    
    # Базовый queryset
    users = User.objects.all()
    
    # Применяем поиск
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Фильтр по роли
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Сортировка
    users = users.order_by(sort_by)
    
    # Добавляем аннотации для статистики
    users = users.annotate(
        managed_orders_count=Count('managed_orders', distinct=True),
        installation_orders_count=Count('installation_orders', distinct=True),
        total_revenue=Sum('managed_orders__total_cost')
    )
    
    # Статистика для карточек
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    managers_count = User.objects.filter(role='manager').count()
    installers_count = User.objects.filter(role='installer').count()
    
    # Пагинация
    paginator = Paginator(users, 12)  # 12 пользователей на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'sort_by': sort_by,
        'total_users': total_users,
        'active_users': active_users,
        'managers_count': managers_count,
        'installers_count': installers_count,
        'role_choices': User.ROLE_CHOICES,
    }
    
    return render(request, 'user_accounts/user_list.html', context)

@login_required
def user_detail(request, pk):
    """Детальная информация о пользователе - ТОЛЬКО для владельца"""
    if request.user.role != 'owner':
        messages.error(request, 'У вас нет прав для просмотра информации о пользователях.')
        return redirect('dashboard')
    
    user_obj = get_object_or_404(User, pk=pk)
    
    # Статистика пользователя
    today = timezone.now()
    start_of_month = today.replace(day=1)
    
    # Заказы пользователя
    if user_obj.role == 'manager':
        orders = user_obj.managed_orders.all()
        orders_this_month = user_obj.managed_orders.filter(created_at__gte=start_of_month)
        completed_orders = user_obj.managed_orders.filter(status='completed')
        total_revenue = completed_orders.aggregate(total=Sum('total_cost'))['total'] or 0
    elif user_obj.role == 'installer':
        orders = user_obj.installation_orders.all()
        orders_this_month = user_obj.installation_orders.filter(created_at__gte=start_of_month)
        completed_orders = user_obj.installation_orders.filter(status='completed')
        total_revenue = 0
    else:
        orders = []
        orders_this_month = []
        completed_orders = []
        total_revenue = 0
    
    # Расчет зарплаты за текущий месяц
    salary_data = None
    try:
        from finance.utils import calculate_installer_salary, calculate_manager_salary, calculate_owner_salary
        
        if user_obj.role == 'installer':
            salary_data = calculate_installer_salary(user_obj, start_of_month, today)
        elif user_obj.role == 'manager':
            salary_data = calculate_manager_salary(user_obj, start_of_month, today)
        elif user_obj.role == 'owner':
            salary_data = calculate_owner_salary(start_of_month, today)
    except ImportError:
        pass
    
    # Последние заказы
    recent_orders = orders.order_by('-created_at')[:5]
    
    context = {
        'user_obj': user_obj,
        'orders_count': orders.count(),
        'orders_this_month_count': orders_this_month.count(),
        'completed_orders_count': completed_orders.count(),
        'total_revenue': total_revenue,
        'salary_data': salary_data,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'user_accounts/user_detail.html', context)

@login_required
def user_new(request):
    """Создание нового пользователя - ТОЛЬКО для владельца"""
    if request.user.role != 'owner':
        messages.error(request, 'У вас нет прав для создания пользователей.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Пользователь {user.get_full_name()} успешно создан!')
            return redirect('user_detail', pk=user.pk)
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'user_accounts/user_form.html', {'form': form, 'title': 'Создание пользователя'})

@login_required
def user_edit(request, pk):
    """Редактирование пользователя - ТОЛЬКО для владельца"""
    if request.user.role != 'owner':
        messages.error(request, 'У вас нет прав для редактирования пользователей.')
        return redirect('dashboard')
    
    user_obj = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=user_obj)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Пользователь {user.get_full_name()} успешно обновлен!')
            return redirect('user_detail', pk=user.pk)
    else:
        form = CustomUserChangeForm(instance=user_obj)
    
    return render(request, 'user_accounts/user_form.html', {
        'form': form, 
        'user_obj': user_obj, 
        'edit': True,
        'title': f'Редактирование пользователя {user_obj.get_full_name()}'
    })

@login_required
def user_delete(request, pk):
    """Удаление пользователя"""
    if request.user.role != 'owner':
        messages.error(request, 'У вас нет прав для удаления пользователей.')
        return redirect('dashboard')
    
    user_obj = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        if user_obj == request.user:
            messages.error(request, 'Вы не можете удалить самого себя.')
            return redirect('user_list')
        
        username = user_obj.get_full_name()
        user_obj.delete()
        messages.success(request, f'Пользователь {username} успешно удален!')
        return redirect('user_list')
    
    return render(request, 'user_accounts/user_confirm_delete.html', {'user_obj': user_obj})

@login_required
def user_toggle_active(request, pk):
    """Активация/деактивация пользователя"""
    if request.user.role != 'owner':
        return JsonResponse({'success': False, 'error': 'Недостаточно прав'})
    
    if request.method == 'POST':
        user_obj = get_object_or_404(User, pk=pk)
        user_obj.is_active = not user_obj.is_active
        user_obj.save()
        
        status = 'активирован' if user_obj.is_active else 'деактивирован'
        return JsonResponse({
            'success': True, 
            'message': f'Пользователь {user_obj.get_full_name()} {status}',
            'is_active': user_obj.is_active
        })
    
    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'})