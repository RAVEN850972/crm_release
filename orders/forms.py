from django import forms
from .models import Order, OrderItem
from user_accounts.models import User  # Исправлено с accounts.models
from customer_clients.models import Client  # Исправлено с clients.models
from services.models import Service

class OrderForm(forms.ModelForm):
    """Форма для создания и редактирования заказа"""
    class Meta:
        model = Order
        fields = ['client', 'manager', 'status', 'installers']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'installers': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Фильтруем список менеджеров
        self.fields['manager'].queryset = User.objects.filter(role='manager')
        # Фильтруем список монтажников
        self.fields['installers'].queryset = User.objects.filter(role='installer')

class OrderItemForm(forms.ModelForm):
    """Форма для добавления позиции в заказ"""
    class Meta:
        model = OrderItem
        fields = ['service', 'price', 'seller']
        widgets = {
            'service': forms.Select(attrs={'class': 'form-select', 'onchange': 'updatePrice()'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'seller': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Список доступных продавцов - менеджеры и монтажники
        self.fields['seller'].queryset = User.objects.filter(role__in=['manager', 'installer'])