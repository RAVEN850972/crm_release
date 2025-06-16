# calendar_app/serializers.py
from rest_framework import serializers
from .models import InstallationSchedule, RouteOptimization, RoutePoint
from orders.serializers import OrderSerializer
from user_accounts.serializers import UserSerializer

class InstallationScheduleSerializer(serializers.ModelSerializer):
    order_details = OrderSerializer(source='order', read_only=True)
    installers_details = UserSerializer(source='installers', many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    client_name = serializers.CharField(source='order.client.name', read_only=True)
    client_address = serializers.CharField(source='order.client.address', read_only=True)
    client_phone = serializers.CharField(source='order.client.phone', read_only=True)
    manager_name = serializers.CharField(source='order.manager.get_full_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    duration = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = InstallationSchedule
        fields = [
            'id', 'order', 'scheduled_date', 'scheduled_time_start', 'scheduled_time_end',
            'installers', 'status', 'priority', 'estimated_duration', 'actual_start_time',
            'actual_end_time', 'notes', 'travel_time_to', 'travel_distance_to',
            'latitude', 'longitude', 'created_at', 'updated_at',
            # Read-only fields
            'order_details', 'installers_details', 'status_display', 'priority_display',
            'client_name', 'client_address', 'client_phone', 'manager_name',
            'is_overdue', 'duration'
        ]
        read_only_fields = ['created_at', 'updated_at', 'travel_time_to', 'travel_distance_to']
    
    def get_duration(self, obj):
        """Возвращает фактическую продолжительность работ"""
        if obj.duration:
            return str(obj.duration)
        return None
    
    def validate(self, data):
        """Валидация данных"""
        if 'scheduled_time_start' in data and 'scheduled_time_end' in data:
            if data['scheduled_time_start'] >= data['scheduled_time_end']:
                raise serializers.ValidationError(
                    'Время начала должно быть раньше времени окончания'
                )
        
        return data

class RoutePointSerializer(serializers.ModelSerializer):
    schedule_details = InstallationScheduleSerializer(source='schedule', read_only=True)
    client_name = serializers.CharField(source='schedule.order.client.name', read_only=True)
    client_address = serializers.CharField(source='schedule.order.client.address', read_only=True)
    order_id = serializers.IntegerField(source='schedule.order.id', read_only=True)
    
    class Meta:
        model = RoutePoint
        fields = [
            'id', 'sequence_number', 'arrival_time', 'departure_time',
            'schedule', 'schedule_details', 'client_name', 'client_address', 'order_id'
        ]

class RouteOptimizationSerializer(serializers.ModelSerializer):
    installer_name = serializers.CharField(source='installer.get_full_name', read_only=True)
    points = RoutePointSerializer(source='routepoint_set', many=True, read_only=True)
    schedules_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = RouteOptimization
        fields = [
            'id', 'date', 'installer', 'installer_name', 'total_distance',
            'total_travel_time', 'start_location', 'is_optimized',
            'created_at', 'updated_at', 'points', 'schedules_count'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_schedules_count(self, obj):
        """Количество монтажей в маршруте"""
        return obj.schedules.count()