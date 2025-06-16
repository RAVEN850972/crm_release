from rest_framework import serializers
from user_accounts.models import User
from customer_clients.models import Client
from services.models import Service
from orders.models import Order, OrderItem
from finance.models import Transaction, SalaryPayment

class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role', 'phone', 'role_display', 'full_name']
        extra_kwargs = {'password': {'write_only': True}}

class ClientSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    
    class Meta:
        model = Client
        fields = ['id', 'name', 'address', 'phone', 'source', 'source_display', 'created_at']

class ServiceSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    profit_margin = serializers.SerializerMethodField()
    
    class Meta:
        model = Service
        fields = ['id', 'name', 'cost_price', 'selling_price', 'category', 'category_display', 'profit_margin', 'created_at']
    
    def get_profit_margin(self, obj):
        if obj.selling_price > 0:
            return float((obj.selling_price - obj.cost_price) / obj.selling_price * 100)
        return 0

class OrderItemSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_category = serializers.CharField(source='service.category', read_only=True)
    service_category_display = serializers.CharField(source='service.get_category_display', read_only=True)
    service_cost_price = serializers.DecimalField(source='service.cost_price', max_digits=10, decimal_places=2, read_only=True)
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    profit = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'service', 'price', 'seller', 'created_at',
            'service_name', 'service_category', 'service_category_display',
            'service_cost_price', 'seller_name', 'profit'
        ]
    
    def get_profit(self, obj):
        return float(obj.price - obj.service.cost_price)

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_phone = serializers.CharField(source='client.phone', read_only=True)
    client_address = serializers.CharField(source='client.address', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    installers_names = serializers.SerializerMethodField(read_only=True)
    items_count = serializers.SerializerMethodField()
    total_profit = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'client', 'manager', 'status', 'installers', 'total_cost', 'items', 
            'created_at', 'completed_at', 'client_name', 'client_phone', 'client_address', 
            'manager_name', 'status_display', 'installers_names', 'items_count', 'total_profit'
        ]
    
    def get_installers_names(self, obj):
        return [{'id': installer.id, 'name': installer.get_full_name()} for installer in obj.installers.all()]
    
    def get_items_count(self, obj):
        return obj.items.count()
    
    def get_total_profit(self, obj):
        total_profit = sum(
            float(item.price - item.service.cost_price) 
            for item in obj.items.all()
        )
        return total_profit

class TransactionSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    order_display = serializers.CharField(source='order.__str__', read_only=True)
    
    class Meta:
        model = Transaction
        fields = ['id', 'type', 'amount', 'description', 'order', 'created_at', 'type_display', 'order_display']

class SalaryPaymentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_role = serializers.CharField(source='user.get_role_display', read_only=True)
    period_display = serializers.SerializerMethodField()
    
    class Meta:
        model = SalaryPayment
        fields = ['id', 'user', 'amount', 'period_start', 'period_end', 'created_at', 'user_name', 'user_role', 'period_display']
    
    def get_period_display(self, obj):
        return f"{obj.period_start} - {obj.period_end}"