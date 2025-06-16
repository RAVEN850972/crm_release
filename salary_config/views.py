# salary_config/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from decimal import Decimal
import json

from user_accounts.models import User
from .models import (
   SalaryConfig, ManagerSalaryConfig, InstallerSalaryConfig, 
   OwnerSalaryConfig, UserSalaryAssignment, SalaryAdjustment
)
from .forms import (
   SalaryConfigForm, ManagerSalaryConfigForm, InstallerSalaryConfigForm,
   OwnerSalaryConfigForm, UserSalaryAssignmentForm, SalaryAdjustmentForm,
   BulkSalaryAssignmentForm, SalaryCalculationForm, SalaryConfigCopyForm
)
from .services import SalaryCalculationService, SalaryConfigService

@login_required
def salary_config_list(request):
   """Список конфигураций зарплат"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для просмотра настроек зарплат.')
       return redirect('dashboard')
   
   configs = SalaryConfig.objects.all().order_by('-created_at')
   
   # Добавляем информацию о назначениях
   for config in configs:
       config.assignments_count = config.usersalaryassignment_set.count()
       config.has_manager_config = hasattr(config, 'manager_config')
       config.has_installer_config = hasattr(config, 'installer_config')
       config.has_owner_config = hasattr(config, 'owner_config')
   
   return render(request, 'salary_config/config_list.html', {'configs': configs})

@login_required
def salary_config_detail(request, pk):
   """Детали конфигурации зарплаты"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для просмотра настроек зарплат.')
       return redirect('dashboard')
   
   config = get_object_or_404(SalaryConfig, pk=pk)
   assignments = UserSalaryAssignment.objects.filter(config=config).select_related('user')
   
   context = {
       'config': config,
       'assignments': assignments,
       'has_manager_config': hasattr(config, 'manager_config'),
       'has_installer_config': hasattr(config, 'installer_config'),
       'has_owner_config': hasattr(config, 'owner_config'),
   }
   
   return render(request, 'salary_config/config_detail.html', context)

@login_required
def salary_config_create(request):
   """Создание новой конфигурации зарплаты"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для создания настроек зарплат.')
       return redirect('dashboard')
   
   if request.method == 'POST':
       config_form = SalaryConfigForm(request.POST)
       manager_form = ManagerSalaryConfigForm(request.POST)
       installer_form = InstallerSalaryConfigForm(request.POST)
       owner_form = OwnerSalaryConfigForm(request.POST)
       
       if all([config_form.is_valid(), manager_form.is_valid(), 
               installer_form.is_valid(), owner_form.is_valid()]):
           
           with transaction.atomic():
               config = config_form.save()
               
               # Создаем настройки для всех ролей
               manager_config = manager_form.save(commit=False)
               manager_config.config = config
               manager_config.save()
               
               installer_config = installer_form.save(commit=False)
               installer_config.config = config
               installer_config.save()
               
               owner_config = owner_form.save(commit=False)
               owner_config.config = config
               owner_config.save()
           
           messages.success(request, 'Конфигурация зарплаты успешно создана!')
           return redirect('salary_config:config_detail', pk=config.pk)
   else:
       config_form = SalaryConfigForm()
       manager_form = ManagerSalaryConfigForm()
       installer_form = InstallerSalaryConfigForm()
       owner_form = OwnerSalaryConfigForm()
   
   context = {
       'config_form': config_form,
       'manager_form': manager_form,
       'installer_form': installer_form,
       'owner_form': owner_form,
   }
   
   return render(request, 'salary_config/config_form.html', context)

@login_required
def salary_config_edit(request, pk):
   """Редактирование конфигурации зарплаты"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для редактирования настроек зарплат.')
       return redirect('dashboard')
   
   config = get_object_or_404(SalaryConfig, pk=pk)
   
   # Получаем или создаем связанные конфигурации
   manager_config = getattr(config, 'manager_config', None)
   installer_config = getattr(config, 'installer_config', None)
   owner_config = getattr(config, 'owner_config', None)
   
   if request.method == 'POST':
       config_form = SalaryConfigForm(request.POST, instance=config)
       manager_form = ManagerSalaryConfigForm(request.POST, instance=manager_config)
       installer_form = InstallerSalaryConfigForm(request.POST, instance=installer_config)
       owner_form = OwnerSalaryConfigForm(request.POST, instance=owner_config)
       
       if all([config_form.is_valid(), manager_form.is_valid(), 
               installer_form.is_valid(), owner_form.is_valid()]):
           
           with transaction.atomic():
               config = config_form.save()
               
               # Сохраняем или создаем настройки для всех ролей
               manager_config = manager_form.save(commit=False)
               manager_config.config = config
               manager_config.save()
               
               installer_config = installer_form.save(commit=False)
               installer_config.config = config
               installer_config.save()
               
               owner_config = owner_form.save(commit=False)
               owner_config.config = config
               owner_config.save()
           
           messages.success(request, 'Конфигурация зарплаты успешно обновлена!')
           return redirect('salary_config:config_detail', pk=config.pk)
   else:
       config_form = SalaryConfigForm(instance=config)
       manager_form = ManagerSalaryConfigForm(instance=manager_config)
       installer_form = InstallerSalaryConfigForm(instance=installer_config)
       owner_form = OwnerSalaryConfigForm(instance=owner_config)
   
   context = {
       'config': config,
       'config_form': config_form,
       'manager_form': manager_form,
       'installer_form': installer_form,
       'owner_form': owner_form,
       'edit': True,
   }
   
   return render(request, 'salary_config/config_form.html', context)

@login_required
def salary_assignments(request):
   """Управление назначениями конфигураций пользователям"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для управления назначениями зарплат.')
       return redirect('dashboard')
   
   assignments = UserSalaryAssignment.objects.all().select_related('user', 'config')
   users_without_config = SalaryConfigService.get_users_without_config()
   
   context = {
       'assignments': assignments,
       'users_without_config': users_without_config,
   }
   
   return render(request, 'salary_config/assignments.html', context)

@login_required
def salary_assignment_create(request):
   """Создание назначения конфигурации пользователю"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для создания назначений зарплат.')
       return redirect('dashboard')
   
   if request.method == 'POST':
       form = UserSalaryAssignmentForm(request.POST)
       if form.is_valid():
           form.save()
           messages.success(request, 'Конфигурация зарплаты успешно назначена!')
           return redirect('salary_config:assignments')
   else:
       form = UserSalaryAssignmentForm()
   
   return render(request, 'salary_config/assignment_form.html', {'form': form})

@login_required
def salary_assignment_edit(request, pk):
   """Редактирование назначения конфигурации"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для редактирования назначений зарплат.')
       return redirect('dashboard')
   
   assignment = get_object_or_404(UserSalaryAssignment, pk=pk)
   
   if request.method == 'POST':
       form = UserSalaryAssignmentForm(request.POST, instance=assignment)
       if form.is_valid():
           form.save()
           messages.success(request, 'Назначение конфигурации успешно обновлено!')
           return redirect('salary_config:assignments')
   else:
       form = UserSalaryAssignmentForm(instance=assignment)
   
   return render(request, 'salary_config/assignment_form.html', {
       'form': form, 
       'assignment': assignment
   })

@login_required
def salary_assignment_delete(request, pk):
   """Удаление назначения конфигурации"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для удаления назначений зарплат.')
       return redirect('dashboard')
   
   assignment = get_object_or_404(UserSalaryAssignment, pk=pk)
   
   if request.method == 'POST':
       user_name = assignment.user.get_full_name()
       assignment.delete()
       messages.success(request, f'Назначение конфигурации для {user_name} удалено!')
       return redirect('salary_config:assignments')
   
   return render(request, 'salary_config/assignment_confirm_delete.html', {
       'assignment': assignment
   })

@login_required
def bulk_salary_assignment(request):
   """Массовое назначение конфигурации"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для массового назначения зарплат.')
       return redirect('dashboard')
   
   if request.method == 'POST':
       form = BulkSalaryAssignmentForm(request.POST)
       if form.is_valid():
           config = form.cleaned_data['config']
           users = form.cleaned_data['users']
           
           updated_count = 0
           for user in users:
               UserSalaryAssignment.objects.update_or_create(
                   user=user,
                   defaults={'config': config}
               )
               updated_count += 1
           
           messages.success(request, f'Конфигурация назначена {updated_count} пользователям!')
           return redirect('salary_config:assignments')
   else:
       form = BulkSalaryAssignmentForm()
   
   return render(request, 'salary_config/bulk_assignment.html', {'form': form})

@login_required
def salary_adjustments(request):
   """Список корректировок зарплаты"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для просмотра корректировок зарплат.')
       return redirect('dashboard')
   
   adjustments = SalaryAdjustment.objects.all().select_related('user', 'created_by').order_by('-created_at')
   
   # Фильтрация
   user_id = request.GET.get('user')
   adjustment_type = request.GET.get('type')
   
   if user_id:
       adjustments = adjustments.filter(user_id=user_id)
   if adjustment_type:
       adjustments = adjustments.filter(adjustment_type=adjustment_type)
   
   context = {
       'adjustments': adjustments,
       'users': User.objects.filter(role__in=['manager', 'installer', 'owner']),
       'adjustment_types': SalaryAdjustment.ADJUSTMENT_TYPES,
       'current_user_id': user_id,
       'current_type': adjustment_type,
   }
   
   return render(request, 'salary_config/adjustments.html', context)

@login_required
def salary_adjustment_create(request):
   """Создание корректировки зарплаты"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для создания корректировок зарплат.')
       return redirect('dashboard')
   
   if request.method == 'POST':
       form = SalaryAdjustmentForm(request.POST)
       if form.is_valid():
           adjustment = form.save(commit=False)
           adjustment.created_by = request.user
           adjustment.save()
           messages.success(request, 'Корректировка зарплаты успешно создана!')
           return redirect('salary_config:adjustments')
   else:
       form = SalaryAdjustmentForm()
       
       # Предзаполняем период текущим месяцем
       today = timezone.now().date()
       form.fields['period_start'].initial = today.replace(day=1)
       form.fields['period_end'].initial = today
   
   return render(request, 'salary_config/adjustment_form.html', {'form': form})

@login_required
def salary_adjustment_edit(request, pk):
   """Редактирование корректировки зарплаты"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для редактирования корректировок зарплат.')
       return redirect('dashboard')
   
   adjustment = get_object_or_404(SalaryAdjustment, pk=pk)
   
   if request.method == 'POST':
       form = SalaryAdjustmentForm(request.POST, instance=adjustment)
       if form.is_valid():
           form.save()
           messages.success(request, 'Корректировка зарплаты успешно обновлена!')
           return redirect('salary_config:adjustments')
   else:
       form = SalaryAdjustmentForm(instance=adjustment)
   
   return render(request, 'salary_config/adjustment_form.html', {
       'form': form, 
       'adjustment': adjustment
   })

@login_required
def salary_calculation_view(request):
   """Расчет зарплаты с новыми настройками"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для расчета зарплат.')
       return redirect('dashboard')
   
   calculation_result = None
   
   if request.method == 'POST':
       form = SalaryCalculationForm(request.POST)
       if form.is_valid():
           user = form.cleaned_data.get('user')
           start_date = form.cleaned_data['period_start']
           end_date = form.cleaned_data['period_end']
           
           # Преобразуем даты в datetime
           start_datetime = datetime.combine(start_date, datetime.min.time())
           end_datetime = datetime.combine(end_date, datetime.max.time())
           
           if user:
               if user.role == 'installer':
                   calculation_result = SalaryCalculationService.calculate_installer_salary(
                       user, start_datetime, end_datetime
                   )
               elif user.role == 'manager':
                   calculation_result = SalaryCalculationService.calculate_manager_salary(
                       user, start_datetime, end_datetime
                   )
               elif user.role == 'owner':
                   calculation_result = SalaryCalculationService.calculate_owner_salary(
                       start_datetime, end_datetime
                   )
               calculation_result['user'] = user
           else:
               # Расчет для владельца без указания пользователя
               calculation_result = SalaryCalculationService.calculate_owner_salary(
                   start_datetime, end_datetime
               )
               calculation_result['user'] = None
   else:
       form = SalaryCalculationForm()
       
       # Предзаполняем период текущим месяцем
       today = timezone.now().date()
       form.fields['period_start'].initial = today.replace(day=1)
       form.fields['period_end'].initial = today
   
   context = {
       'form': form,
       'calculation_result': calculation_result,
   }
   
   return render(request, 'salary_config/calculation.html', context)

@login_required
def salary_config_copy(request):
   """Копирование конфигурации зарплаты"""
   if request.user.role != 'owner':
       messages.error(request, 'У вас нет прав для копирования конфигураций.')
       return redirect('dashboard')
   
   if request.method == 'POST':
       form = SalaryConfigCopyForm(request.POST)
       if form.is_valid():
           source_config = form.cleaned_data['source_config']
           new_name = form.cleaned_data['new_name']
           new_description = form.cleaned_data['new_description']
           copy_assignments = form.cleaned_data['copy_assignments']
           
           with transaction.atomic():
               # Создаем новую конфигурацию
               new_config = SalaryConfig.objects.create(
                   name=new_name,
                   description=new_description,
                   is_active=True
               )
               
               # Копируем настройки менеджера
               if hasattr(source_config, 'manager_config'):
                   old_manager = source_config.manager_config
                   ManagerSalaryConfig.objects.create(
                       config=new_config,
                       fixed_salary=old_manager.fixed_salary,
                       bonus_per_completed_order=old_manager.bonus_per_completed_order,
                       conditioner_profit_percentage=old_manager.conditioner_profit_percentage,
                       additional_services_profit_percentage=old_manager.additional_services_profit_percentage,
                       installation_profit_percentage=old_manager.installation_profit_percentage,
                       maintenance_profit_percentage=old_manager.maintenance_profit_percentage,
                       dismantling_profit_percentage=old_manager.dismantling_profit_percentage,
                   )
               
               # Копируем настройки монтажника
               if hasattr(source_config, 'installer_config'):
                   old_installer = source_config.installer_config
                   InstallerSalaryConfig.objects.create(
                       config=new_config,
                       payment_per_installation=old_installer.payment_per_installation,
                       additional_services_profit_percentage=old_installer.additional_services_profit_percentage,
                       quality_bonus=old_installer.quality_bonus,
                       penalty_per_complaint=old_installer.penalty_per_complaint,
                   )
               
               # Копируем настройки владельца
               if hasattr(source_config, 'owner_config'):
                   old_owner = source_config.owner_config
                   OwnerSalaryConfig.objects.create(
                       config=new_config,
                       payment_per_installation=old_owner.payment_per_installation,
                       remaining_profit_percentage=old_owner.remaining_profit_percentage,
                   )
               
               # Копируем назначения, если нужно
               if copy_assignments:
                   assignments = UserSalaryAssignment.objects.filter(config=source_config)
                   for assignment in assignments:
                       UserSalaryAssignment.objects.update_or_create(
                           user=assignment.user,
                           defaults={'config': new_config}
                       )
           
           messages.success(request, f'Конфигурация "{new_name}" успешно создана!')
           return redirect('salary_config:config_detail', pk=new_config.pk)
   else:
       form = SalaryConfigCopyForm()
   
   return render(request, 'salary_config/config_copy.html', {'form': form})

@login_required
def auto_assign_default_config(request):
   """Автоматическое назначение конфигурации по умолчанию"""
   if request.user.role != 'owner':
       return JsonResponse({'success': False, 'error': 'Недостаточно прав'})
   
   if request.method == 'POST':
       try:
           assigned_count = SalaryConfigService.bulk_assign_default_config()
           return JsonResponse({
               'success': True, 
               'message': f'Конфигурация назначена {assigned_count} пользователям'
           })
       except Exception as e:
           return JsonResponse({'success': False, 'error': str(e)})
   
   return JsonResponse({'success': False, 'error': 'Метод не поддерживается'})

@login_required
def salary_calculation_api(request):
   """API для расчета зарплаты (для AJAX)"""
   if request.user.role != 'owner':
       return JsonResponse({'success': False, 'error': 'Недостаточно прав'})
   
   if request.method == 'POST':
       try:
           data = json.loads(request.body)
           user_id = data.get('user_id')
           start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d')
           end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d')
           
           # Преобразуем в datetime
           start_datetime = datetime.combine(start_date, datetime.min.time())
           end_datetime = datetime.combine(end_date, datetime.max.time())
           
           if user_id:
               user = get_object_or_404(User, pk=user_id)
               if user.role == 'installer':
                   result = SalaryCalculationService.calculate_installer_salary(
                       user, start_datetime, end_datetime
                   )
               elif user.role == 'manager':
                   result = SalaryCalculationService.calculate_manager_salary(
                       user, start_datetime, end_datetime
                   )
               elif user.role == 'owner':
                   result = SalaryCalculationService.calculate_owner_salary(
                       start_datetime, end_datetime
                   )
               else:
                   return JsonResponse({'success': False, 'error': 'Неизвестная роль пользователя'})
           else:
               result = SalaryCalculationService.calculate_owner_salary(
                   start_datetime, end_datetime
               )
           
           # Конвертируем Decimal в float для JSON
           def convert_decimals(obj):
               if isinstance(obj, Decimal):
                   return float(obj)
               elif isinstance(obj, dict):
                   return {k: convert_decimals(v) for k, v in obj.items()}
               elif isinstance(obj, list):
                   return [convert_decimals(v) for v in obj]
               return obj
           
           result = convert_decimals(result)
           
           return JsonResponse({'success': True, 'data': result})
           
       except Exception as e:
           return JsonResponse({'success': False, 'error': str(e)})
   
   return JsonResponse({'success': False, 'error': 'Метод не поддерживается'})