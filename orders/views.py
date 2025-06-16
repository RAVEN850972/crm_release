from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Order, OrderItem
from .forms import OrderForm, OrderItemForm
from customer_clients.models import Client
from services.models import Service
from user_accounts.models import User

@login_required
def order_list(request):
    """Список заказов с учетом прав доступа"""
    # Для владельца - все заказы
    if request.user.role == 'owner':
        orders = Order.objects.all().order_by('-created_at')
    # Для менеджера - только его заказы
    elif request.user.role == 'manager':
        orders = Order.objects.filter(manager=request.user).order_by('-created_at')
    # Для монтажника - только заказы, где он назначен (ТОЛЬКО ПРОСМОТР)
    else:  # installer
        orders = Order.objects.filter(installers=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
        'can_edit': request.user.role in ['owner', 'manager'],
        'can_create': request.user.role in ['owner', 'manager'],
    }
    
    return render(request, 'orders/order_list.html', context)

@login_required
def order_detail(request, pk):
    """Детальная информация о заказе с учетом прав"""
    # Для владельца - любой заказ
    if request.user.role == 'owner':
        order = get_object_or_404(Order, pk=pk)
    # Для менеджера - только его заказы
    elif request.user.role == 'manager':
        order = get_object_or_404(Order, pk=pk, manager=request.user)
    # Для монтажника - заказы, где он назначен (ТОЛЬКО ПРОСМОТР)
    else:  # installer
        order = get_object_or_404(Order, pk=pk, installers=request.user)
    
    items = order.items.all()
    installers = order.installers.all()
    
    context = {
        'order': order,
        'items': items,
        'installers': installers,
        'can_edit': request.user.role in ['owner', 'manager'],
        'can_add_items': request.user.role in ['owner', 'manager'],
        'can_change_status': request.user.role in ['owner', 'manager'] or 
                           (request.user.role == 'installer' and request.user in order.installers.all()),
    }
    
    return render(request, 'orders/order_detail.html', context)

@login_required
def order_new(request):
    """Создание нового заказа - ТОЛЬКО для владельца и менеджера"""
    if request.user.role not in ['owner', 'manager']:
        messages.error(request, 'У вас нет прав для создания заказов.')
        return redirect('order_list')
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if request.user.role == 'manager':
                order.manager = request.user
            order.save()
            order.installers.set(form.cleaned_data['installers'])
            messages.success(request, 'Заказ успешно создан!')
            return redirect('order_detail', pk=order.pk)
    else:
        form = OrderForm()
        if request.user.role == 'manager':
            form.fields['manager'].initial = request.user
            form.fields['manager'].disabled = True
    
    return render(request, 'orders/order_form.html', {'form': form})

@login_required
def order_edit(request, pk):
    """Редактирование заказа - ТОЛЬКО для владельца и менеджера"""
    if request.user.role not in ['owner', 'manager']:
        messages.error(request, 'У вас нет прав для редактирования заказов.')
        return redirect('order_list')
    
    # Для владельца - любой заказ
    if request.user.role == 'owner':
        order = get_object_or_404(Order, pk=pk)
    # Для менеджера - только его заказы
    else:  # manager
        order = get_object_or_404(Order, pk=pk, manager=request.user)
    
    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save()
            order.installers.set(form.cleaned_data['installers'])
            messages.success(request, 'Заказ успешно обновлен!')
            return redirect('order_detail', pk=order.pk)
    else:
        form = OrderForm(instance=order)
        if request.user.role == 'manager':
            form.fields['manager'].disabled = True
    
    return render(request, 'orders/order_form.html', {'form': form, 'edit': True})

@login_required
def order_add_item(request, pk):
    """Добавление позиции в заказ - ТОЛЬКО для владельца и менеджера"""
    if request.user.role not in ['owner', 'manager']:
        messages.error(request, 'У вас нет прав для добавления позиций в заказ.')
        return redirect('order_detail', pk=pk)
    
    # Для владельца - любой заказ
    if request.user.role == 'owner':
        order = get_object_or_404(Order, pk=pk)
    # Для менеджера - только его заказы
    else:  # manager
        order = get_object_or_404(Order, pk=pk, manager=request.user)
    
    if request.method == 'POST':
        form = OrderItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.order = order
            if not item.seller:
                item.seller = request.user
            item.save()
            messages.success(request, 'Позиция успешно добавлена в заказ!')
            return redirect('order_detail', pk=order.pk)
    else:
        form = OrderItemForm()
        form.fields['seller'].initial = request.user
    
    return render(request, 'orders/order_item_form.html', {'form': form, 'order': order})

@login_required
def order_change_status(request, pk):
    """Изменение статуса заказа с ограниченными правами для монтажника"""
    # Для владельца - любой заказ
    if request.user.role == 'owner':
        order = get_object_or_404(Order, pk=pk)
    # Для менеджера - только его заказы
    elif request.user.role == 'manager':
        order = get_object_or_404(Order, pk=pk, manager=request.user)
    # Для монтажника - только заказы, где он назначен, и только на "Завершен"
    else:  # installer
        order = get_object_or_404(Order, pk=pk, installers=request.user)
        status = request.POST.get('status')
        if status != 'completed':
            messages.error(request, 'Монтажники могут только завершать заказы.')
            return redirect('order_detail', pk=pk)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(Order.STATUS_CHOICES).keys():
            order.status = status
            if status == 'completed':
                order.completed_at = timezone.now()
            order.save()
            messages.success(request, f'Статус заказа изменен на "{dict(Order.STATUS_CHOICES)[status]}"!')
        else:
            messages.error(request, 'Некорректный статус заказа.')
    
    return redirect('order_detail', pk=pk)

@login_required
def my_orders(request):
    """Специальная страница для монтажников - только их заказы"""
    if request.user.role != 'installer':
        return redirect('order_list')
    
    # Только заказы монтажника
    orders = Order.objects.filter(installers=request.user).order_by('-created_at')
    
    # Статистика для монтажника
    total_orders = orders.count()
    completed_orders = orders.filter(status='completed').count()
    in_progress_orders = orders.filter(status='in_progress').count()
    
    context = {
        'orders': orders,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'in_progress_orders': in_progress_orders,
        'is_installer_view': True,
    }
    
    return render(request, 'orders/installer_orders.html', context)