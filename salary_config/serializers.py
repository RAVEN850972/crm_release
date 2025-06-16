# salary_config/serializers.py
from rest_framework import serializers
from .models import (
    SalaryConfig, ManagerSalaryConfig, InstallerSalaryConfig, 
    OwnerSalaryConfig, UserSalaryAssignment, SalaryAdjustment
)
from user_accounts.serializers import UserSerializer

class ManagerSalaryConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerSalaryConfig
        exclude = ['config']

class InstallerSalaryConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstallerSalaryConfig
        exclude = ['config']

class OwnerSalaryConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = OwnerSalaryConfig
        exclude = ['config']

class SalaryConfigSerializer(serializers.ModelSerializer):
    manager_config = ManagerSalaryConfigSerializer(read_only=True)
    installer_config = InstallerSalaryConfigSerializer(read_only=True)
    owner_config = OwnerSalaryConfigSerializer(read_only=True)
    assignments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SalaryConfig
        fields = [
            'id', 'name', 'description', 'is_active', 'created_at', 'updated_at',
            'manager_config', 'installer_config', 'owner_config', 'assignments_count'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_assignments_count(self, obj):
        return obj.usersalaryassignment_set.count()

class UserSalaryAssignmentSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    config_name = serializers.CharField(source='config.name', read_only=True)
    config_active = serializers.BooleanField(source='config.is_active', read_only=True)
    
    class Meta:
        model = UserSalaryAssignment
        fields = [
            'id', 'user', 'config', 'assigned_at',
            'user_details', 'config_name', 'config_active'
        ]
        read_only_fields = ['assigned_at']

class SalaryAdjustmentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    adjustment_type_display = serializers.CharField(source='get_adjustment_type_display', read_only=True)
    
    class Meta:
        model = SalaryAdjustment
        fields = [
            'id', 'user', 'adjustment_type', 'amount', 'reason',
            'period_start', 'period_end', 'created_by', 'created_at',
            'user_name', 'created_by_name', 'adjustment_type_display'
        ]
        read_only_fields = ['created_by', 'created_at']

class SalaryCalculationSerializer(serializers.Serializer):
    """Сериализатор для результатов расчета зарплаты"""
    config_name = serializers.CharField()
    total_salary = serializers.DecimalField(max_digits=10, decimal_places=2)
    period = serializers.CharField()
    
    # Поля для монтажника
    installation_pay = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    installation_count = serializers.IntegerField(required=False)
    additional_pay = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    additional_services_count = serializers.IntegerField(required=False)
    
    # Поля для менеджера
    fixed_salary = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    orders_bonus = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    completed_orders_count = serializers.IntegerField(required=False)
    sales_bonus = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    sales_details = serializers.DictField(required=False)
    
    # Поля для владельца
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    total_cost_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    gross_profit = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    estimated_staff_payments = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    remaining_profit = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    owner_profit_share = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    
    # Общие поля
    adjustments = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    adjustments_details = serializers.ListField(required=False)