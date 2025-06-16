# calendar_app/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from datetime import datetime, timedelta, time
from django.db.models import Q

from .models import InstallationSchedule, RouteOptimization
from .services import CalendarService, RouteOptimizationService
from .serializers import InstallationScheduleSerializer, RouteOptimizationSerializer
from orders.models import Order
from user_accounts.models import User

@method_decorator(login_required, name='dispatch')
class CalendarView(APIView):
    """API для работы с календарем монтажей"""
    
    def get(self, request):
        """Получение календаря на период"""
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        installer_id = request.GET.get('installer_id')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'Параметры start_date и end_date обязательны'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Неверный формат даты. Используйте YYYY-MM-DD'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Фильтруем расписания
        schedules_query = InstallationSchedule.objects.filter(
            scheduled_date__range=(start_date, end_date)
        ).select_related('order', 'order__client', 'order__manager')
        
        if installer_id:
            schedules_query = schedules_query.filter(installers__id=installer_id)
        
        # Проверяем права доступа
        if request.user.role == 'installer':
            schedules_query = schedules_query.filter(installers=request.user)
        elif request.user.role == 'manager':
            schedules_query = schedules_query.filter(order__manager=request.user)
        
        schedules = schedules_query.distinct().order_by('scheduled_date', 'scheduled_time_start')
        
        # Группируем по дням
        calendar_data = {}
        for schedule in schedules:
            date_str = schedule.scheduled_date.strftime('%Y-%m-%d')
            if date_str not in calendar_data:
                calendar_data[date_str] = []
            
            calendar_data[date_str].append({
                'id': schedule.id,
                'order_id': schedule.order.id,
                'client_name': schedule.order.client.name,
                'client_address': schedule.order.client.address,
                'client_phone': schedule.order.client.phone,
                'manager': schedule.order.manager.get_full_name(),
                'start_time': schedule.scheduled_time_start.strftime('%H:%M'),
                'end_time': schedule.scheduled_time_end.strftime('%H:%M'),
                'status': schedule.status,
                'status_display': schedule.get_status_display(),
                'priority': schedule.priority,
                'priority_display': schedule.get_priority_display(),
                'installers': [
                    {
                        'id': installer.id,
                        'name': installer.get_full_name()
                    }
                    for installer in schedule.installers.all()
                ],
                'notes': schedule.notes,
                'is_overdue': schedule.is_overdue,
                'estimated_duration': str(schedule.estimated_duration) if schedule.estimated_duration else None,
            })
        
        return Response({
            'calendar': calendar_data,
            'total_schedules': schedules.count()
        })
    
    def post(self, request):
        """Создание нового расписания монтажа"""
        data = request.data
        
        try:
            order = get_object_or_404(Order, id=data.get('order_id'))
            
            # Проверяем права
            if request.user.role == 'manager' and order.manager != request.user:
                return Response(
                    {'error': 'Нет прав для создания расписания этого заказа'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            elif request.user.role not in ['owner', 'manager']:
                return Response(
                    {'error': 'Недостаточно прав'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Парсим данные
            scheduled_date = datetime.strptime(data.get('scheduled_date'), '%Y-%m-%d').date()
            start_time = datetime.strptime(data.get('start_time'), '%H:%M').time()
            end_time = datetime.strptime(data.get('end_time'), '%H:%M').time()
            installer_ids = data.get('installer_ids', [])
            
            # Дополнительные параметры
            priority = data.get('priority', 'normal')
            notes = data.get('notes', '')
            estimated_duration = None
            
            if data.get('estimated_duration'):
                hours, minutes = map(int, data.get('estimated_duration').split(':'))
                estimated_duration = timedelta(hours=hours, minutes=minutes)
            
            # Создаем расписание
            schedule = CalendarService.create_schedule(
                order=order,
                scheduled_date=scheduled_date,
                start_time=start_time,
                end_time=end_time,
                installers_ids=installer_ids,
                priority=priority,
                notes=notes,
                estimated_duration=estimated_duration
            )
            
            serializer = InstallationScheduleSerializer(schedule)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Ошибка создания расписания: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(login_required, name='dispatch')
class ScheduleDetailView(APIView):
    """Детальная работа с конкретным расписанием"""
    
    def get(self, request, schedule_id):
        """Получение детальной информации о расписании"""
        schedule = get_object_or_404(InstallationSchedule, id=schedule_id)
        
        # Проверяем права доступа
        if request.user.role == 'installer' and request.user not in schedule.installers.all():
            return Response({'error': 'Нет доступа'}, status=status.HTTP_403_FORBIDDEN)
        elif request.user.role == 'manager' and schedule.order.manager != request.user:
            return Response({'error': 'Нет доступа'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = InstallationScheduleSerializer(schedule)
        return Response(serializer.data)
    
    def put(self, request, schedule_id):
        """Обновление расписания"""
        schedule = get_object_or_404(InstallationSchedule, id=schedule_id)
        
        # Проверяем права
        if request.user.role not in ['owner', 'manager']:
            return Response({'error': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)
        
        if request.user.role == 'manager' and schedule.order.manager != request.user:
            return Response({'error': 'Нет прав для изменения этого расписания'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = InstallationScheduleSerializer(schedule, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, schedule_id):
        """Удаление расписания"""
        schedule = get_object_or_404(InstallationSchedule, id=schedule_id)
        
        # Проверяем права
        if request.user.role not in ['owner', 'manager']:
            return Response({'error': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)
        
        if request.user.role == 'manager' and schedule.order.manager != request.user:
            return Response({'error': 'Нет прав для удаления этого расписания'}, status=status.HTTP_403_FORBIDDEN)
        
        schedule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@method_decorator(login_required, name='dispatch')
class StartWorkView(APIView):
    """Начало выполнения монтажа"""
    
    def post(self, request, schedule_id):
        """Отметка о начале работы"""
        schedule = get_object_or_404(InstallationSchedule, id=schedule_id)
        
        # Проверяем, что пользователь - один из назначенных монтажников
        if request.user.role != 'installer' or request.user not in schedule.installers.all():
            return Response({'error': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)
        
        if schedule.status != 'scheduled':
            return Response({'error': 'Работа уже начата или завершена'}, status=status.HTTP_400_BAD_REQUEST)
        
        schedule.status = 'in_progress'
        schedule.actual_start_time = timezone.now()
        schedule.save()
        
        # Обновляем статус заказа
        if schedule.order.status == 'new':
            schedule.order.status = 'in_progress'
            schedule.order.save()
        
        return Response({
            'message': 'Работа начата',
            'actual_start_time': schedule.actual_start_time,
            'status': schedule.status
        })

@method_decorator(login_required, name='dispatch')
class CompleteWorkView(APIView):
    """Завершение монтажа"""
    
    def post(self, request, schedule_id):
        """Отметка о завершении работы"""
        schedule = get_object_or_404(InstallationSchedule, id=schedule_id)
        
        # Проверяем, что пользователь - один из назначенных монтажников
        if request.user.role != 'installer' or request.user not in schedule.installers.all():
            return Response({'error': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)
        
        if schedule.status != 'in_progress':
            return Response({'error': 'Работа не была начата'}, status=status.HTTP_400_BAD_REQUEST)
        
        schedule.status = 'completed'
        schedule.actual_end_time = timezone.now()
        schedule.save()
        
        # Обновляем статус заказа на завершенный
        schedule.order.status = 'completed'
        schedule.order.completed_at = timezone.now()
        schedule.order.save()
        
        return Response({
            'message': 'Работа завершена',
            'actual_end_time': schedule.actual_end_time,
            'duration': str(schedule.duration),
            'status': schedule.status
        })

@method_decorator(login_required, name='dispatch')
class RouteOptimizationView(APIView):
    """API для оптимизации маршрутов"""
    
    def get(self, request):
        """Получение оптимизированного маршрута"""
        installer_id = request.GET.get('installer_id')
        date_str = request.GET.get('date')
        
        if not installer_id or not date_str:
            return Response(
                {'error': 'Параметры installer_id и date обязательны'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            installer_id = int(installer_id)
        except ValueError:
            return Response(
                {'error': 'Неверный формат параметров'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем права доступа
        if request.user.role == 'installer' and request.user.id != installer_id:
            return Response({'error': 'Нет доступа'}, status=status.HTTP_403_FORBIDDEN)
        
        # Получаем сводку маршрута
        route_summary = RouteOptimizationService.get_route_summary(installer_id, date)
        
        if not route_summary:
            return Response({'message': 'Маршрут не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(route_summary)
    
    def post(self, request):
        """Создание/обновление оптимизированного маршрута"""
        installer_id = request.data.get('installer_id')
        date_str = request.data.get('date')
        
        if not installer_id or not date_str:
            return Response(
                {'error': 'Параметры installer_id и date обязательны'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            installer_id = int(installer_id)
        except ValueError:
            return Response(
                {'error': 'Неверный формат параметров'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем права доступа
        if request.user.role not in ['owner', 'manager']:
            return Response({'error': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Оптимизируем маршрут
            route = RouteOptimizationService.optimize_daily_route(installer_id, date)
            
            if not route:
                return Response({'message': 'Нет расписаний для оптимизации'}, status=status.HTTP_404_NOT_FOUND)
            
            # Получаем сводку
            route_summary = RouteOptimizationService.get_route_summary(installer_id, date)
            
            return Response({
                'message': 'Маршрут успешно оптимизирован',
                'route': route_summary
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Ошибка оптимизации маршрута: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(login_required, name='dispatch')
class InstallerScheduleView(APIView):
    """Расписание конкретного монтажника"""
    
    def get(self, request, installer_id):
        """Получение расписания монтажника"""
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not start_date or not end_date:
            # По умолчанию текущая неделя
            today = timezone.now().date()
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Неверный формат даты'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Проверяем права доступа
        if request.user.role == 'installer' and request.user.id != int(installer_id):
            return Response({'error': 'Нет доступа'}, status=status.HTTP_403_FORBIDDEN)
        
        schedule_data = CalendarService.get_installer_schedule(installer_id, start_date, end_date)
        
        return Response({
            'installer_id': installer_id,
            'start_date': start_date,
            'end_date': end_date,
            'schedule': schedule_data
        })

@method_decorator(login_required, name='dispatch')
class AvailabilityCheckView(APIView):
    """Проверка доступности монтажников"""
    
    def post(self, request):
        """Проверка доступности на указанное время"""
        installer_ids = request.data.get('installer_ids', [])
        date_str = request.data.get('date')
        start_time_str = request.data.get('start_time')
        end_time_str = request.data.get('end_time')
        
        if not all([installer_ids, date_str, start_time_str, end_time_str]):
            return Response(
                {'error': 'Все параметры обязательны'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
        except ValueError:
            return Response(
                {'error': 'Неверный формат данных'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conflicts = CalendarService.check_installer_availability(
            installer_ids, date, start_time, end_time
        )
        
        return Response({
            'available': len(conflicts) == 0,
            'conflicts': conflicts,
            'message': 'Все монтажники доступны' if not conflicts else f'Конфликты: {", ".join(conflicts)}'
        })