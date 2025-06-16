# salary_config/forms.py
from django import forms
from django.core.exceptions import ValidationError
from user_accounts.models import User
from .models import (
    SalaryConfig, ManagerSalaryConfig, InstallerSalaryConfig, 
    OwnerSalaryConfig, UserSalaryAssignment, SalaryAdjustment
)

class SalaryConfigForm(forms.ModelForm):
    """Форма для создания/редактирования конфигурации зарплат"""
    class Meta:
        model = SalaryConfig
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ManagerSalaryConfigForm(forms.ModelForm):
    """Форма для настройки зарплаты менеджера"""
    class Meta:
        model = ManagerSalaryConfig
        exclude = ['config']
        widgets = {
            'fixed_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bonus_per_completed_order': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'conditioner_profit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'additional_services_profit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'installation_profit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'maintenance_profit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'dismantling_profit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
        }

class InstallerSalaryConfigForm(forms.ModelForm):
    """Форма для настройки зарплаты монтажника"""
    class Meta:
        model = InstallerSalaryConfig
        exclude = ['config']
        widgets = {
            'payment_per_installation': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'additional_services_profit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'quality_bonus': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'penalty_per_complaint': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class OwnerSalaryConfigForm(forms.ModelForm):
    """Форма для настройки зарплаты владельца"""
    class Meta:
        model = OwnerSalaryConfig
        exclude = ['config']
        widgets = {
            'payment_per_installation': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'remaining_profit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
        }

class UserSalaryAssignmentForm(forms.ModelForm):
    """Форма для назначения конфигурации зарплаты пользователю"""
    class Meta:
        model = UserSalaryAssignment
        fields = ['user', 'config']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'config': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Показываем только активные конфигурации
        self.fields['config'].queryset = SalaryConfig.objects.filter(is_active=True)
        # Показываем только пользователей с ролями
        self.fields['user'].queryset = User.objects.filter(
            role__in=['manager', 'installer', 'owner']
        ).order_by('role', 'last_name', 'first_name')

class SalaryAdjustmentForm(forms.ModelForm):
    """Форма для корректировки зарплаты"""
    class Meta:
        model = SalaryAdjustment
        exclude = ['created_by']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'adjustment_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'period_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'period_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Показываем только сотрудников
        self.fields['user'].queryset = User.objects.filter(
            role__in=['manager', 'installer', 'owner']
        ).order_by('role', 'last_name', 'first_name')
    
    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get('period_start')
        period_end = cleaned_data.get('period_end')
        
        if period_start and period_end:
            if period_start > period_end:
                raise ValidationError('Дата начала периода не может быть позже даты окончания')
        
        return cleaned_data

class BulkSalaryAssignmentForm(forms.Form):
    """Форма для массового назначения конфигурации зарплаты"""
    config = forms.ModelChoiceField(
        queryset=SalaryConfig.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Конфигурация зарплаты"
    )
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role__in=['manager', 'installer', 'owner']),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label="Пользователи"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['users'].queryset = User.objects.filter(
            role__in=['manager', 'installer', 'owner']
        ).order_by('role', 'last_name', 'first_name')

class SalaryCalculationForm(forms.Form):
    """Форма для расчета зарплаты за период"""
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(role__in=['manager', 'installer', 'owner']),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Сотрудник",
        required=False,
        help_text="Оставьте пустым для расчета зарплаты владельца"
    )
    period_start = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Начало периода"
    )
    period_end = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Конец периода"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(
            role__in=['manager', 'installer', 'owner']
        ).order_by('role', 'last_name', 'first_name')
    
    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get('period_start')
        period_end = cleaned_data.get('period_end')
        
        if period_start and period_end:
            if period_start > period_end:
                raise ValidationError('Дата начала периода не может быть позже даты окончания')
        
        return cleaned_data

class SalaryConfigCopyForm(forms.Form):
    """Форма для копирования конфигурации зарплаты"""
    source_config = forms.ModelChoiceField(
        queryset=SalaryConfig.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Исходная конфигурация"
    )
    new_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Название новой конфигурации"
    )
    new_description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label="Описание новой конфигурации",
        required=False
    )
    copy_assignments = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Скопировать назначения пользователям",
        required=False,
        help_text="Если отмечено, новая конфигурация будет назначена тем же пользователям"
    )