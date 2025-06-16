from django import forms
from .models import Service

class ServiceForm(forms.ModelForm):
    """Форма для создания и редактирования услуги"""
    class Meta:
        model = Service
        fields = ['name', 'cost_price', 'selling_price', 'category']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }