from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Client
from .forms import ClientForm
from orders.models import Order

@login_required
def client_list(request):
    """Список клиентов"""
    # Фильтрация по источнику, если указан
    source = request.GET.get('source')
    if source:
        clients = Client.objects.filter(source=source).order_by('-created_at')
    else:
        clients = Client.objects.all().order_by('-created_at')
    
    # Поиск по имени или телефону
    search_query = request.GET.get('search')
    if search_query:
        clients = clients.filter(
            Q(name__icontains=search_query) | 
            Q(phone__icontains=search_query) |
            Q(address__icontains=search_query)
        )
    
    return render(request, 'clients/list.html', {'clients': clients})

@login_required
def client_detail(request, pk):
    """Детальная информация о клиенте"""
    client = get_object_or_404(Client, pk=pk)
    
    # Получаем все заказы этого клиента
    orders = Order.objects.filter(client=client).order_by('-created_at')
    
    return render(request, 'customer_clients/client_detail.html', {
        'client': client,
        'orders': orders
    })

@login_required
def client_new(request):
    """Создание нового клиента"""
    # Только владелец и менеджер могут создавать клиентов
    if request.user.role not in ['owner', 'manager']:
        messages.error(request, 'У вас нет прав для создания клиентов.')
        return redirect('client_list')
    
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, 'Клиент успешно создан!')
            return redirect('client_detail', pk=client.pk)
    else:
        form = ClientForm()
    
    return render(request, 'customer_clients/client_form.html', {'form': form})

@login_required
def client_edit(request, pk):
    """Редактирование клиента"""
    # Только владелец и менеджер могут редактировать клиентов
    if request.user.role not in ['owner', 'manager']:
        messages.error(request, 'У вас нет прав для редактирования клиентов.')
        return redirect('client_list')
    
    client = get_object_or_404(Client, pk=pk)
    
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            client = form.save()
            messages.success(request, 'Клиент успешно обновлен!')
            return redirect('client_detail', pk=client.pk)
    else:
        form = ClientForm(instance=client)
    
    return render(request, 'customer_clients/client_form.html', {'form': form, 'edit': True})