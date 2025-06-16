from django import forms
from .models import Transaction, SalaryPayment

class TransactionForm(forms.ModelForm):
    """Форма для создания и редактирования финансовой транзакции"""
    class Meta:
        model = Transaction
        fields = ['type', 'amount', 'description', 'order']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.Select(attrs={'class': 'form-select'}),
        }

class SalaryPaymentForm(forms.ModelForm):
    """Форма для создания выплаты зарплаты"""
    class Meta:
        model = SalaryPayment
        fields = ['amount', 'period_start', 'period_end']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'period_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'period_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }