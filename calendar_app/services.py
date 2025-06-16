# calendar_app/services.py
import requests
from datetime import datetime, timedelta, time
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from typing import List, Dict, Tuple, Optional
import math

from .models import InstallationSchedule, RouteOptimization, RoutePoint
from user_accounts.models import User

class GeocodeService:
    """Сервис для геокодирования адресов"""
    
    @staticmethod
    def geocode_address(address: str) -> Optional[Tuple[float, float]]:
        """
        Получает координаты по адресу через Яндекс.Карты API
        Возвращает (latitude, longitude) или None
        """
        if not address:
            return None
            
        # Можете заменить на ваш API ключ
        api_key = getattr(settings, 'YANDEX_MAPS_API_KEY', '')
        
        if not api_key:
            # Заглушка для тестирования - случайные координаты Москвы
            import random
            return (
                55.7558 + random.uniform(-0.1, 0.1),  # Широта Москвы +- погрешность
                37.6176 + random.uniform(-0.1, 0.1)   # Долгота Москвы +- погрешность
            )
        
        url = "https://geocode-maps.yandex.ru/1.x/"
        params = {
            'apikey': api_key,
            'geocode': address,
            'format': 'json',
            'results': 1
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            feature_member = data['response']['GeoObjectCollection']['featureMember']
            if not feature_member:
                return None
                
            coords = feature_member[0]['GeoObject']['Point']['pos'].split()
            longitude, latitude = float(coords[0]), float(coords[1])
            return (latitude, longitude)
            
        except Exception as e:
            print(f"Ошибка геокодирования для адреса '{address}': {e}")
            return None

class RouteCalculationService:
    """Сервис для расчета расстояний и времени между точками"""
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Рассчитывает расстояние между двумя точками по формуле гаверсинусов
        Возвращает расстояние в километрах
        """
        R = 6371  # Радиус Земли в км
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    @staticmethod
    def estimate_travel_time(distance_km: float) -> timedelta:
        """
        Оценивает время в пути на основе расстояния
        Средняя скорость в городе: 30 км/ч
        """
        avg_speed_kmh = 30
        travel_hours = distance_km / avg_speed_kmh
        
        # Добавляем время на пробки и остановки (20% надбавка)
        travel_hours *= 1.2
        
        return timedelta(hours=travel_hours)

class CalendarService:
    """Основной сервис для работы с календарем монтажей"""
    
    @staticmethod
    def create_schedule(order, scheduled_date, start_time, end_time, installers_ids: List[int], **kwargs):
        """Создает расписание монтажа"""
        
        # Проверяем доступность монтажников
        conflicts = CalendarService.check_installer_availability(
            installers_ids, scheduled_date, start_time, end_time
        )
        
        if conflicts:
            raise ValueError(f"Конфликт расписания для монтажников: {conflicts}")
        
        # Получаем координаты адреса клиента
        coordinates = GeocodeService.geocode_address(order.client.address)
        
        # Создаем расписание
        schedule = InstallationSchedule.objects.create(
            order=order,
            scheduled_date=scheduled_date,
            scheduled_time_start=start_time,
            scheduled_time_end=end_time,
            latitude=coordinates[0] if coordinates else None,
            longitude=coordinates[1] if coordinates else None,
            **kwargs
        )
        
        # Добавляем монтажников
        schedule.installers.set(installers_ids)
        
        return schedule
    
    @staticmethod
    def check_installer_availability(installer_ids: List[int], date, start_time, end_time) -> List[str]:
        """Проверяет доступность монтажников на указанное время"""
        conflicts = []
        
        for installer_id in installer_ids:
            installer = User.objects.get(id=installer_id)
            
            # Ищем пересекающиеся расписания
            overlapping = InstallationSchedule.objects.filter(
                installers=installer,
                scheduled_date=date,
                status__in=['scheduled', 'in_progress']
            ).filter(
                Q(scheduled_time_start__lt=end_time) & 
                Q(scheduled_time_end__gt=start_time)
            )
            
            if overlapping.exists():
                conflicts.append(f"{installer.get_full_name()}")
        
        return conflicts
    
    @staticmethod
    def get_installer_schedule(installer_id: int, start_date, end_date) -> List[Dict]:
        """Получает расписание монтажника на период"""
        schedules = InstallationSchedule.objects.filter(
            installers__id=installer_id,
            scheduled_date__range=(start_date, end_date)
        ).select_related('order', 'order__client').order_by('scheduled_date', 'scheduled_time_start')
        
        result = []
        for schedule in schedules:
            result.append({
                'id': schedule.id,
                'order_id': schedule.order.id,
                'client_name': schedule.order.client.name,
                'client_address': schedule.order.client.address,
                'client_phone': schedule.order.client.phone,
                'date': schedule.scheduled_date,
                'start_time': schedule.scheduled_time_start,
                'end_time': schedule.scheduled_time_end,
                'status': schedule.status,
                'priority': schedule.priority,
                'notes': schedule.notes,
                'estimated_duration': schedule.estimated_duration,
            })
        
        return result

class RouteOptimizationService:
    """Сервис для оптимизации маршрутов монтажников"""
    
    @staticmethod
    def optimize_daily_route(installer_id: int, date) -> RouteOptimization:
        """Оптимизирует маршрут монтажника на день"""
        
        installer = User.objects.get(id=installer_id)
        
        # Получаем все запланированные монтажи на день
        schedules = InstallationSchedule.objects.filter(
            installers=installer,
            scheduled_date=date,
            status='scheduled'
        ).select_related('order', 'order__client')
        
        if not schedules:
            return None
        
        # Создаем или получаем объект маршрута
        route, created = RouteOptimization.objects.get_or_create(
            installer=installer,
            date=date,
            defaults={
                'start_location': 'Склад компании',  # Можно сделать настраиваемым
                'is_optimized': False
            }
        )
        
        # Очищаем существующие точки маршрута
        RoutePoint.objects.filter(route=route).delete()
        
        # Добавляем координаты для адресов, если их нет
        for schedule in schedules:
            if not schedule.latitude or not schedule.longitude:
                coordinates = GeocodeService.geocode_address(schedule.order.client.address)
                if coordinates:
                    schedule.latitude = coordinates[0]
                    schedule.longitude = coordinates[1]
                    schedule.save()
        
        # Применяем алгоритм оптимизации (упрощенный)
        optimized_schedules = RouteOptimizationService._simple_optimization(list(schedules))
        
        # Создаем точки маршрута
        total_distance = 0
        total_travel_time = timedelta()
        current_time = time(8, 0)  # Начало рабочего дня
        
        for i, schedule in enumerate(optimized_schedules, 1):
            # Рассчитываем время прибытия и отъезда
            if i == 1:
                arrival_time = current_time
            else:
                # Время прибытия = время отъезда с предыдущей точки + время в пути
                prev_schedule = optimized_schedules[i-2]
                if schedule.latitude and schedule.longitude and prev_schedule.latitude and prev_schedule.longitude:
                    distance = RouteCalculationService.calculate_distance(
                        prev_schedule.latitude, prev_schedule.longitude,
                        schedule.latitude, schedule.longitude
                    )
                    travel_time = RouteCalculationService.estimate_travel_time(distance)
                    
                    total_distance += distance
                    total_travel_time += travel_time
                    
                    # Обновляем данные в расписании
                    schedule.travel_distance_to = distance
                    schedule.travel_time_to = travel_time
                    schedule.save()
                    
                    current_time_delta = timedelta(
                        hours=current_time.hour,
                        minutes=current_time.minute
                    ) + travel_time
                    
                    hours = int(current_time_delta.total_seconds() // 3600)
                    minutes = int((current_time_delta.total_seconds() % 3600) // 60)
                    arrival_time = time(hours % 24, minutes)
                else:
                    arrival_time = current_time
            
            # Время отъезда = время прибытия + продолжительность работ
            if schedule.estimated_duration:
                departure_delta = timedelta(
                    hours=arrival_time.hour,
                    minutes=arrival_time.minute
                ) + schedule.estimated_duration
                
                hours = int(departure_delta.total_seconds() // 3600)
                minutes = int((departure_delta.total_seconds() % 3600) // 60)
                departure_time = time(hours % 24, minutes)
                current_time = departure_time
            else:
                # По умолчанию 2 часа на монтаж
                departure_delta = timedelta(
                    hours=arrival_time.hour,
                    minutes=arrival_time.minute
                ) + timedelta(hours=2)  # Исправлено: убрано дублирование hours
                
                hours = int(departure_delta.total_seconds() // 3600)
                minutes = int((departure_delta.total_seconds() % 3600) // 60)
                departure_time = time(hours % 24, minutes)
                current_time = departure_time
            
            # Создаем точку маршрута
            RoutePoint.objects.create(
                route=route,
                schedule=schedule,
                sequence_number=i,
                arrival_time=arrival_time,
                departure_time=departure_time
            )
        
        # Обновляем общие данные маршрута
        route.total_distance = total_distance
        route.total_travel_time = total_travel_time
        route.is_optimized = True
        route.save()
        
        return route
    
    @staticmethod
    def _simple_optimization(schedules: List[InstallationSchedule]) -> List[InstallationSchedule]:
        """
        Простой алгоритм оптимизации маршрута по принципу "ближайшего соседа"
        В реальном проекте можно использовать более сложные алгоритмы
        """
        if not schedules:
            return []
        
        # Фильтруем только те расписания, у которых есть координаты
        schedules_with_coords = [s for s in schedules if s.latitude and s.longitude]
        schedules_without_coords = [s for s in schedules if not s.latitude or not s.longitude]
        
        if not schedules_with_coords:
            return schedules
        
        optimized = []
        remaining = schedules_with_coords.copy()
        
        # Начинаем с расписания с наивысшим приоритетом
        current = min(remaining, key=lambda x: {
            'urgent': 0, 'high': 1, 'normal': 2, 'low': 3
        }.get(x.priority, 2))
        
        optimized.append(current)
        remaining.remove(current)
        
        # Алгоритм ближайшего соседа
        while remaining:
            current_lat, current_lon = current.latitude, current.longitude
            
            nearest = min(remaining, key=lambda s: RouteCalculationService.calculate_distance(
                current_lat, current_lon, s.latitude, s.longitude
            ))
            
            optimized.append(nearest)
            remaining.remove(nearest)
            current = nearest
        
        # Добавляем расписания без координат в конец
        optimized.extend(schedules_without_coords)
        
        return optimized
    
    @staticmethod
    def get_route_summary(installer_id: int, date) -> Dict:
        """Получает сводку по маршруту монтажника на день"""
        try:
            route = RouteOptimization.objects.get(installer_id=installer_id, date=date)
            points = RoutePoint.objects.filter(route=route).select_related(
                'schedule', 'schedule__order', 'schedule__order__client'
            ).order_by('sequence_number')
            
            return {
                'route_id': route.id,
                'installer': route.installer.get_full_name(),
                'date': route.date,
                'total_distance': route.total_distance,
                'total_travel_time': route.total_travel_time,
                'is_optimized': route.is_optimized,
                'start_location': route.start_location,
                'points': [
                    {
                        'sequence': point.sequence_number,
                        'arrival_time': point.arrival_time,
                        'departure_time': point.departure_time,
                        'client_name': point.schedule.order.client.name,
                        'client_address': point.schedule.order.client.address,
                        'client_phone': point.schedule.order.client.phone,
                        'order_id': point.schedule.order.id,
                        'status': point.schedule.status,
                        'priority': point.schedule.priority,
                        'travel_distance': point.schedule.travel_distance_to,
                        'travel_time': point.schedule.travel_time_to,
                    }
                    for point in points
                ]
            }
        except RouteOptimization.DoesNotExist:
            return None