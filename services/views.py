from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Service
from .forms import ServiceForm

@login_required
def service_list(request):
    """Список услуг"""
    # Фильтрация по категории, если указана
    category = request.GET.get('category')
    if category:
        services = Service.objects.filter(category=category).order_by('name')
    else:
        services = Service.objects.all().order_by('name')
    
    return render(request, 'services/services.html', {'services': services})

@login_required
def service_detail(request, pk):
    """Детальная информация об услуге"""
    service = get_object_or_404(Service, pk=pk)
    return render(request, 'services/service_detail.html', {'service': service})

@login_required
def service_new(request):
    """Создание новой услуги"""
    # Только владелец может создавать услуги
    if request.user.role != 'owner':
        messages.error(request, 'У вас нет прав для создания услуг.')
        return redirect('service_list')
    
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save()
            messages.success(request, 'Услуга успешно создана!')
            return redirect('service_detail', pk=service.pk)
    else:
        form = ServiceForm()
    
    return render(request, 'services/service_form.html', {'form': form})

@login_required
def service_edit(request, pk):
    """Редактирование услуги"""
    # Только владелец может редактировать услуги
    if request.user.role != 'owner':
        messages.error(request, 'У вас нет прав для редактирования услуг.')
        return redirect('service_list')
    
    service = get_object_or_404(Service, pk=pk)
    
    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            service = form.save()
            messages.success(request, 'Услуга успешно обновлена!')
            return redirect('service_detail', pk=service.pk)
    else:
        form = ServiceForm(instance=service)
    
    return render(request, 'services/service_form.html', {'form': form, 'edit': True})