# orders/serializers.py
from rest_framework import serializers
from .models import Order, OrderItem
from user_accounts.models import User
from customer_clients.models import Client
from services.models import Service

class OrderSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_phone = serializers.CharField(source='client.phone', read_only=True)
    client_address = serializers.CharField(source='client.address', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    installers_names = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'client', 'manager', 'status', 'installers', 'total_cost',
            'created_at', 'completed_at', 'client_name', 'client_phone', 
            'client_address', 'manager_name', 'status_display', 'installers_names'
        ]

    def get_installers_names(self, obj):
        return [{'id': installer.id, 'name': installer.get_full_name()} 
                for installer in obj.installers.all()]

class OrderItemSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_category = serializers.CharField(source='service.category', read_only=True)
    service_category_display = serializers.CharField(source='service.get_category_display', read_only=True)
    service_cost_price = serializers.DecimalField(source='service.cost_price', max_digits=10, decimal_places=2, read_only=True)
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'service', 'price', 'seller', 'created_at',
            'service_name', 'service_category', 'service_category_display',
            'service_cost_price', 'seller_name'
        ]