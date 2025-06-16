from django.contrib import admin
from .models import Service

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'cost_price', 'selling_price', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('name',)
    date_hierarchy = 'created_at'