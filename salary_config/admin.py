# salary_config/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    SalaryConfig, ManagerSalaryConfig, InstallerSalaryConfig, 
    OwnerSalaryConfig, UserSalaryAssignment, SalaryAdjustment
)

class ManagerSalaryConfigInline(admin.StackedInline):
    model = ManagerSalaryConfig
    extra = 0
    fields = (
        'fixed_salary',
        ('bonus_per_completed_order',),
        ('conditioner_profit_percentage', 'additional_services_profit_percentage'),
        ('installation_profit_percentage', 'maintenance_profit_percentage', 'dismantling_profit_percentage'),
    )

class InstallerSalaryConfigInline(admin.StackedInline):
    model = InstallerSalaryConfig
    extra = 0
    fields = (
        ('payment_per_installation', 'additional_services_profit_percentage'),
        ('quality_bonus', 'penalty_per_complaint'),
    )

class OwnerSalaryConfigInline(admin.StackedInline):
    model = OwnerSalaryConfig
    extra = 0
    fields = (
        ('payment_per_installation', 'remaining_profit_percentage'),
    )

@admin.register(SalaryConfig)
class SalaryConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active_indicator', 'assigned_users_count', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [ManagerSalaryConfigInline, InstallerSalaryConfigInline, OwnerSalaryConfigInline]
    
    def is_active_indicator(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #28a745;">✓ Активна</span>')
        return format_html('<span style="color: #dc3545;">✗ Неактивна</span>')
    is_active_indicator.short_description = 'Статус'
    
    def assigned_users_count(self, obj):
        count = obj.usersalaryassignment_set.count()
        return f"{count} пользовател{'ь' if count == 1 else 'ей' if count < 5 else 'ей'}"
    assigned_users_count.short_description = 'Назначено пользователям'

@admin.register(UserSalaryAssignment)
class UserSalaryAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_role', 'config', 'config_active', 'assigned_at')
    list_filter = ('config__is_active', 'user__role', 'assigned_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'config__name')
    raw_id_fields = ('user',)
    
    def user_role(self, obj):
        return obj.user.get_role_display()
    user_role.short_description = 'Роль'
    user_role.admin_order_field = 'user__role'
    
    def config_active(self, obj):
        if obj.config.is_active:
            return format_html('<span style="color: #28a745;">✓</span>')
        return format_html('<span style="color: #dc3545;">✗</span>')
    config_active.short_description = 'Активна'
    config_active.admin_order_field = 'config__is_active'

@admin.register(SalaryAdjustment)
class SalaryAdjustmentAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'adjustment_type_colored', 'amount_colored', 'period_display', 
        'created_by', 'created_at'
    )
    list_filter = ('adjustment_type', 'created_at', 'period_start')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'reason')
    raw_id_fields = ('user', 'created_by')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'adjustment_type', 'amount', 'reason')
        }),
        ('Период', {
            'fields': ('period_start', 'period_end')
        }),
        ('Системная информация', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at',)
    
    def adjustment_type_colored(self, obj):
        colors = {
            'bonus': '#28a745',
            'penalty': '#dc3545',
            'correction': '#ffc107'
        }
        color = colors.get(obj.adjustment_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_adjustment_type_display()
        )
    adjustment_type_colored.short_description = 'Тип'
    adjustment_type_colored.admin_order_field = 'adjustment_type'
    
    def amount_colored(self, obj):
        if obj.amount > 0:
            color = '#28a745'
            sign = '+'
        else:
            color = '#dc3545'
            sign = ''
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{}</span>',
            color, sign, obj.amount
        )
    amount_colored.short_description = 'Сумма'
    amount_colored.admin_order_field = 'amount'
    
    def period_display(self, obj):
        return f"{obj.period_start} - {obj.period_end}"
    period_display.short_description = 'Период'
    
    def save_model(self, request, obj, form, change):
        if not change:  # При создании
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

# Дополнительная настройка админки
admin.site.site_header = "CRM Администрирование"
admin.site.site_title = "CRM Admin"
admin.site.index_title = "Управление системой"