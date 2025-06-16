# Проверка текущей роли
from user_accounts.models import User
user = User.objects.get(username='root')
print(user.role)  # Посмотрите текущее значение
print(User.ROLE_CHOICES)  # Посмотрите допустимые значения