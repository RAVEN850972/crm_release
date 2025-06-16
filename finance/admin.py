from django.contrib import admin
from .models import Transaction, SalaryPayment

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('type', 'amount', 'description', 'order', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('description',)
    date_hierarchy = 'created_at'

@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'period_start', 'period_end', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    date_hierarchy = 'created_at'