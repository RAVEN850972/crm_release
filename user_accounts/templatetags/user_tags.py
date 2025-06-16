from django import template

register = template.Library()

@register.filter
def role_color(role):
    """Возвращает цвет для роли пользователя"""
    colors = {
        'owner': 'warning',
        'manager': 'success', 
        'installer': 'danger'
    }
    return colors.get(role, 'secondary')

@register.filter
def status_color(status):
    """Возвращает цвет для статуса заказа"""
    colors = {
        'new': 'warning',
        'in_progress': 'primary',
        'completed': 'success'
    }
    return colors.get(status, 'secondary')