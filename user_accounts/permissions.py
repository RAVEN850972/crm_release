from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Разрешение проверяет, является ли пользователь владельцем или администратором.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.role == 'owner' or request.user.is_staff)

class IsManager(permissions.BasePermission):
    """
    Разрешение проверяет, является ли пользователь менеджером.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'manager'

class IsInstaller(permissions.BasePermission):
    """
    Разрешение проверяет, является ли пользователь монтажником.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'installer'

class IsOwnerOrManagerForSalary(permissions.BasePermission):
    """
    Разрешение для просмотра зарплат только себе (для менеджера или монтажника) 
    или всем (для владельца).
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Владелец может просматривать все зарплаты
        if request.user.role == 'owner' or request.user.is_staff:
            return True
        
        # Другие пользователи могут просматривать только свою зарплату
        user_id = view.kwargs.get('user_id')
        return str(request.user.id) == str(user_id)