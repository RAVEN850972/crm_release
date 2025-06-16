# calendar_app/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import InstallationSchedule, RouteOptimization, RoutePoint

class RoutePointInline(admin.TabularInline):
    model = RoutePoint
    extra = 0
    readonly_fields = ['arrival_time', 'departure_time']
    fields = ['sequence_number', 'schedule', 'arrival_time', 'departure_time']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('schedule', 'schedule__order', 'schedule__order__client')

@admin.register(InstallationSchedule)
class InstallationScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'order_link', 'client_name', 'scheduled_date', 'scheduled_time_range',
        'status_colored', 'priority_colored', 'installers_list', 'is_overdue_indicator'
    ]
    
    list_filter = [
        'status', 'priority', 'scheduled_date', 'created_at',
        ('installers', admin.RelatedOnlyFieldListFilter)
    ]
    
    search_fields = [
        'order__id', 'order__client__name', 'order__client__phone',
        'order__client__address', 'notes'
    ]
    
    readonly_fields = [
        'created_at', 'updated_at', 'is_overdue', 'duration',
        'travel_time_to', 'travel_distance_to'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('order', 'status', 'priority')
        }),
        ('Расписание', {
            'fields': (
                'scheduled_date', 'scheduled_time_start', 'scheduled_time_end',
                'estimated_duration'
            )
        }),
        ('Монтажники', {
            'fields': ('installers',)
        }),
        ('Фактическое выполнение', {
            'fields': ('actual_start_time', 'actual_end_time', 'duration'),
            'classes': ('collapse',)
        }),
        ('Геолокация и маршрутизация', {
            'fields': ('latitude', 'longitude', 'travel_distance_to', 'travel_time_to'),
            'classes': ('collapse',)
        }),
        ('Дополнительно', {
            'fields': ('notes', 'created_at', 'updated_at', 'is_overdue'),
            'classes': ('collapse',)
        })
    )
    
    filter_horizontal = ['installers']
    date_hierarchy = 'scheduled_date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order', 'order__client', 'order__manager'
        ).prefetch_related('installers')
    
    def order_link(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, f'Заказ #{obj.order.id}')
    order_link.short_description = 'Заказ'
    order_link.admin_order_field = 'order'
    
    def client_name(self, obj):
        return obj.order.client.name
    client_name.short_description = 'Клиент'
    client_name.admin_order_field = 'order__client__name'
    
    def scheduled_time_range(self, obj):
        return f"{obj.scheduled_time_start} - {obj.scheduled_time_end}"
    scheduled_time_range.short_description = 'Время'
    
    def status_colored(self, obj):
        colors = {
            'scheduled': '#007bff',
            'in_progress': '#ffc107',
            'completed': '#28a745',
            'cancelled': '#dc3545',
            'rescheduled': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'Статус'
    status_colored.admin_order_field = 'status'
    
    def priority_colored(self, obj):
        colors = {
            'low': '#6c757d',
            'normal': '#007bff',
            'high': '#ffc107',
            'urgent': '#dc3545'
        }
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_colored.short_description = 'Приоритет'
    priority_colored.admin_order_field = 'priority'
    
    def installers_list(self, obj):
        installers = obj.installers.all()
        if not installers:
            return '-'
        return ', '.join([installer.get_full_name() for installer in installers])
    installers_list.short_description = 'Монтажники'
    
    def is_overdue_indicator(self, obj):
        if obj.is_overdue:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">⚠ Просрочено</span>'
            )
        return format_html('<span style="color: #28a745;">✓ В срок</span>')
    is_overdue_indicator.short_description = 'Статус выполнения'

@admin.register(RouteOptimization)
class RouteOptimizationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'installer_name', 'date', 'schedules_count', 'total_distance',
        'total_travel_time', 'is_optimized_indicator', 'created_at'
    ]
    
    list_filter = [
        'date', 'is_optimized', 'created_at',
        ('installer', admin.RelatedOnlyFieldListFilter)
    ]
    
    search_fields = [
        'installer__first_name', 'installer__last_name', 'installer__username'
    ]
    
    readonly_fields = [
        'total_distance', 'total_travel_time', 'is_optimized',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('installer', 'date', 'start_location')
        }),
        ('Результаты оптимизации', {
            'fields': (
                'total_distance', 'total_travel_time', 'is_optimized',
                'created_at', 'updated_at'
            )
        })
    )
    
    inlines = [RoutePointInline]
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('installer').prefetch_related('schedules')
    
    def installer_name(self, obj):
        return obj.installer.get_full_name()
    installer_name.short_description = 'Монтажник'
    installer_name.admin_order_field = 'installer__last_name'
    
    def schedules_count(self, obj):
        count = obj.schedules.count()
        return f"{count} монтаж{'ей' if count != 1 else ''}"
    schedules_count.short_description = 'Количество монтажей'
    
    def is_optimized_indicator(self, obj):
        if obj.is_optimized:
            return format_html('<span style="color: #28a745;">✓ Оптимизирован</span>')
        return format_html('<span style="color: #ffc107;">⚠ Не оптимизирован</span>')
    is_optimized_indicator.short_description = 'Оптимизация'
    is_optimized_indicator.admin_order_field = 'is_optimized'

@admin.register(RoutePoint)
class RoutePointAdmin(admin.ModelAdmin):
    list_display = [
        'route_info', 'sequence_number', 'schedule_info', 'client_name',
        'arrival_time', 'departure_time'
    ]
    
    list_filter = [
        'route__date', 'route__installer',
        ('route', admin.RelatedOnlyFieldListFilter)
    ]
    
    search_fields = [
        'route__installer__first_name', 'route__installer__last_name',
        'schedule__order__client__name', 'schedule__order__id'
    ]
    
    readonly_fields = ['arrival_time', 'departure_time']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'route', 'route__installer', 'schedule', 'schedule__order', 'schedule__order__client'
        )
    
    def route_info(self, obj):
        return f"{obj.route.installer.get_full_name()} - {obj.route.date}"
    route_info.short_description = 'Маршрут'
    route_info.admin_order_field = 'route__date'
    
    def schedule_info(self, obj):
        return f"Заказ #{obj.schedule.order.id}"
    schedule_info.short_description = 'Расписание'
    schedule_info.admin_order_field = 'schedule__order__id'
    
    def client_name(self, obj):
        return obj.schedule.order.client.name
    client_name.short_description = 'Клиент'
    client_name.admin_order_field = 'schedule__order__client__name'