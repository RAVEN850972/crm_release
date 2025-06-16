from django.contrib import admin
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'address', 'source', 'created_at')
    list_filter = ('source', 'created_at')
    search_fields = ('name', 'phone', 'address')
    date_hierarchy = 'created_at'