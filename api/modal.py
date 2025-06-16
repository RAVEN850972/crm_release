# api/modal.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from customer_clients.models import Client
from services.models import Service
from orders.models import Order, OrderItem
from user_accounts.models import User
from finance.models import Transaction, SalaryPayment

from .serializers import (
    ClientSerializer, ServiceSerializer, OrderSerializer, 
    OrderItemSerializer, UserSerializer, TransactionSerializer, 
    SalaryPaymentSerializer
)

@method_decorator(login_required, name='dispatch')
class ModalClientDataView(APIView):
    """
    API-эндпоинт для получения и обновления данных клиента в модальном окне
    """
    def get(self, request, client_id=None):
        # Если указан ID клиента - возвращаем данные для редактирования
        if client_id:
            client = get_object_or_404(Client, id=client_id)
            serializer = ClientSerializer(client)
            return Response(serializer.data)
        
        # Если ID не указан - возвращаем данные для создания нового клиента
        sources = dict(Client.SOURCE_CHOICES)
        return Response({
            'sources': [{'value': key, 'label': value} for key, value in sources.items()]
        })
    
    def post(self, request):
        # Создание нового клиента
        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            client = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, client_id):
        # Обновление существующего клиента
        client = get_object_or_404(Client, id=client_id)
        serializer = ClientSerializer(client, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(login_required, name='dispatch')
class ModalOrderDataView(APIView):
    """
    API-эндпоинт для получения и обновления данных заказа в модальном окне
    """
    def get(self, request, order_id=None):
        # Данные для формы создания/редактирования заказа
        clients = Client.objects.all().values('id', 'name', 'phone')
        managers = User.objects.filter(role='manager').values('id', 'first_name', 'last_name')
        installers = User.objects.filter(role='installer').values('id', 'first_name', 'last_name')
        statuses = dict(Order.STATUS_CHOICES)
        
        data = {
            'clients': list(clients),
            'managers': list(managers),
            'installers': list(installers),
            'statuses': [{'value': key, 'label': value} for key, value in statuses.items()]
        }
        
        # Если указан ID заказа - возвращаем данные для редактирования
        if order_id:
            order = get_object_or_404(Order, id=order_id)
            serializer = OrderSerializer(order)
            data['order'] = serializer.data
            
            # Добавляем данные о позициях заказа
            items = OrderItem.objects.filter(order=order)
            item_serializer = OrderItemSerializer(items, many=True)
            data['items'] = item_serializer.data
            
            # Добавляем данные для позиций заказа
            services = Service.objects.all().values('id', 'name', 'category', 'selling_price')
            sellers = User.objects.filter(role__in=['manager', 'installer']).values('id', 'first_name', 'last_name', 'role')
            data['services'] = list(services)
            data['sellers'] = list(sellers)
        
        return Response(data)
    
    def post(self, request):
        # Создание нового заказа
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            order = serializer.save()
            
            # Добавление позиций заказа, если они есть в запросе
            if 'items' in request.data and isinstance(request.data['items'], list):
                for item_data in request.data['items']:
                    item_data['order'] = order.id
                    item_serializer = OrderItemSerializer(data=item_data)
                    if item_serializer.is_valid():
                        item_serializer.save()
            
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, order_id):
        # Обновление существующего заказа
        order = get_object_or_404(Order, id=order_id)
        serializer = OrderSerializer(order, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(login_required, name='dispatch')
class ModalOrderItemDataView(APIView):
    """
    API-эндпоинт для добавления и удаления позиций в заказе
    """
    def get(self, request, order_id):
        try:
            # Данные для формы добавления позиции
            order = get_object_or_404(Order, id=order_id)
            services = Service.objects.all().values('id', 'name', 'category', 'selling_price')
            sellers = User.objects.filter(role__in=['manager', 'installer']).values('id', 'first_name', 'last_name', 'role')
            
            # Добавляем display имена для категорий
            category_choices = dict(Service.CATEGORY_CHOICES)
            services_list = []
            for service in services:
                service_dict = dict(service)
                service_dict['category_display'] = category_choices.get(service['category'], service['category'])
                services_list.append(service_dict)
            
            return Response({
                'order': OrderSerializer(order).data,
                'services': services_list,
                'sellers': list(sellers)
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, order_id):
        try:
            # Добавление новой позиции в заказ
            order = get_object_or_404(Order, id=order_id)
            
            # Проверяем права доступа
            if request.user.role not in ['owner', 'manager']:
                return Response({'error': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)
            
            # Получаем данные из запроса
            service_id = request.data.get('service')
            price = request.data.get('price')
            seller_id = request.data.get('seller')
            
            # Валидация данных
            if not service_id:
                return Response({'error': 'Поле service обязательно'}, status=status.HTTP_400_BAD_REQUEST)
            if not price:
                return Response({'error': 'Поле price обязательно'}, status=status.HTTP_400_BAD_REQUEST)
            if not seller_id:
                return Response({'error': 'Поле seller обязательно'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Получаем связанные объекты
            try:
                service = Service.objects.get(id=service_id)
                seller = User.objects.get(id=seller_id)
            except Service.DoesNotExist:
                return Response({'error': 'Услуга не найдена'}, status=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                return Response({'error': 'Продавец не найден'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Создаем позицию заказа напрямую
            item = OrderItem.objects.create(
                order=order,
                service=service,
                price=price,
                seller=seller
            )
            
            # Обновляем данные заказа
            order.refresh_from_db()
            
            # Возвращаем обновленные данные
            item_response_data = {
                'id': item.id,
                'order': order.id,
                'service': service.id,
                'price': str(item.price),
                'seller': seller.id,
                'created_at': item.created_at.isoformat(),
                'service_name': service.name,
                'service_category': service.category,
                'service_category_display': service.get_category_display(),
                'service_cost_price': str(service.cost_price),
                'seller_name': seller.get_full_name()
            }
            
            order_response_data = OrderSerializer(order).data
            
            return Response({
                'item': item_response_data,
                'order': order_response_data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            print("Error in post method:", str(e))
            print("Traceback:", traceback.format_exc())
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, order_id, item_id):
        try:
            # Удаление позиции из заказа
            order = get_object_or_404(Order, id=order_id)
            item = get_object_or_404(OrderItem, id=item_id, order=order)
            
            # Проверяем права доступа
            if request.user.role not in ['owner', 'manager']:
                return Response({'error': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)
            
            item.delete()
            
            # Обновляем данные заказа
            order.refresh_from_db()
            
            return Response({
                'order': OrderSerializer(order).data,
                'message': 'Позиция успешно удалена'
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(login_required, name='dispatch')
class ModalTransactionDataView(APIView):
    """
    API-эндпоинт для работы с финансовыми транзакциями в модальном окне
    """
    def get(self, request, transaction_id=None):
        # Данные для формы создания/редактирования транзакции
        types = dict(Transaction.TYPE_CHOICES)
        orders = Order.objects.all().select_related('client').values('id', 'client__name')
        
        data = {
            'types': [{'value': key, 'label': value} for key, value in types.items()],
            'orders': list(orders)
        }
        
        # Если указан ID транзакции - возвращаем данные для редактирования
        if transaction_id:
            transaction = get_object_or_404(Transaction, id=transaction_id)
            serializer = TransactionSerializer(transaction)
            data['transaction'] = serializer.data
        
        return Response(data)
    
    def post(self, request):
        # Создание новой транзакции
        serializer = TransactionSerializer(data=request.data)
        if serializer.is_valid():
            transaction = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, transaction_id):
        # Обновление существующей транзакции
        transaction = get_object_or_404(Transaction, id=transaction_id)
        serializer = TransactionSerializer(transaction, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(login_required, name='dispatch')
class ModalSalaryPaymentDataView(APIView):
    """
    API-эндпоинт для работы с выплатами зарплаты в модальном окне
    """
    def get(self, request, user_id):
        try:
            # Данные для формы выплаты зарплаты
            user = get_object_or_404(User, id=user_id)
            
            # Расчет зарплаты
            from finance.utils import calculate_installer_salary, calculate_manager_salary, calculate_owner_salary
            
            if user.role == 'installer':
                salary_data = calculate_installer_salary(user)
            elif user.role == 'manager':
                salary_data = calculate_manager_salary(user)
            else:  # owner
                salary_data = calculate_owner_salary()
            
            return Response({
                'user': UserSerializer(user).data,
                'salary_data': salary_data
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, user_id):
        try:
            # Создание выплаты зарплаты
            user = get_object_or_404(User, id=user_id)
            
            # Добавляем пользователя к данным выплаты
            payment_data = request.data.copy()
            payment_data['user'] = user.id
            
            serializer = SalaryPaymentSerializer(data=payment_data)
            if serializer.is_valid():
                payment = serializer.save()
                
                # Создаем соответствующую транзакцию расхода
                transaction_data = {
                    'type': 'expense',
                    'amount': payment.amount,
                    'description': f'Выплата зарплаты {user.get_full_name()} за период {payment.period_start} - {payment.period_end}',
                    'order': None
                }
                transaction_serializer = TransactionSerializer(data=transaction_data)
                if transaction_serializer.is_valid():
                    transaction_serializer.save()
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)