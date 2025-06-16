from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'manager', 'status', 'total_cost', 'created_at', 'completed_at')
    list_filter = ('status', 'manager', 'created_at')
    search_fields = ('client__name', 'id')
    readonly_fields = ('total_cost',)
    inlines = [OrderItemInline]
    filter_horizontal = ('installers',)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'service', 'price', 'seller', 'created_at')
    list_filter = ('order__status', 'service__category', 'seller', 'created_at')
    search_fields = ('order__id', 'service__name', 'seller__username')