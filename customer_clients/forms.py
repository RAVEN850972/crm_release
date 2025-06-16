from django import forms
from .models import Client

class ClientForm(forms.ModelForm):
    """Форма для создания и редактирования клиента"""
    class Meta:
        model = Client
        fields = ['name', 'address', 'phone', 'source']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'type': 'tel'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
        }