# Инструкция по запуску CRM системы на Windows

## Требования к системе

### Минимальные характеристики
- **ОС**: Windows 10/11 или Windows Server 2019+
- **RAM**: 4 GB (рекомендуется 8 GB)
- **CPU**: 2 ядра
- **Диск**: 10 GB свободного места
- **Сеть**: Доступ к интернету

### Необходимое ПО
- Python 3.8+ 
- Git
- Текстовый редактор (VS Code, Notepad++)

## Шаг 1: Установка Python

### Скачивание Python
1. Перейдите на [python.org](https://www.python.org/downloads/)
2. Скачайте последнюю версию Python 3.x для Windows
3. **ВАЖНО**: При установке обязательно отметьте "Add Python to PATH"

### Проверка установки
Откройте Command Prompt (cmd) и выполните:
```cmd
python --version
pip --version
```

## Шаг 2: Установка Git

### Скачивание Git
1. Перейдите на [git-scm.com](https://git-scm.com/download/win)
2. Скачайте и установите Git for Windows
3. При установке оставьте настройки по умолчанию

### Проверка установки
```cmd
git --version
```

## Шаг 3: Скачивание проекта

### Создание рабочей папки
```cmd
mkdir C:\CRM
cd C:\CRM
```

### Клонирование репозитория
```cmd
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ> crm-project
cd crm-project
```

*Если у вас нет Git репозитория, просто скопируйте файлы проекта в папку `C:\CRM\crm-project`*

## Шаг 4: Настройка виртуального окружения

### Создание виртуального окружения
```cmd
cd C:\CRM\crm-project
python -m venv venv
```

### Активация виртуального окружения
```cmd
venv\Scripts\activate
```

*После активации в начале строки появится `(venv)`*

### Установка зависимостей
```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

## Шаг 5: Настройка переменных окружения

### Создание файла .env
Создайте файл `.env` в корне проекта (`C:\CRM\crm-project\.env`) с содержимым:

```env
# Основные настройки Django
DJANGO_SECRET_KEY=your-very-long-and-secure-secret-key-here-change-this-12345
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,*

# База данных SQLite (простой вариант)
DJANGO_DB_ENGINE=django.db.backends.sqlite3
DJANGO_DB_NAME=C:\CRM\crm-project\db.sqlite3

# Email настройки (для тестирования)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# API ключи (опционально)
YANDEX_MAPS_API_KEY=
```

### Генерация секретного ключа
```cmd
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Скопируйте полученный ключ и замените `your-very-long-and-secure-secret-key-here-change-this-12345` в файле .env

## Шаг 6: Инициализация базы данных

### Убедитесь, что виртуальное окружение активно
```cmd
cd C:\CRM\crm-project
venv\Scripts\activate
```

### Применение миграций
```cmd
python manage.py makemigrations
python manage.py migrate
```

### Создание суперпользователя
```cmd
python manage.py createsuperuser
```

Введите данные администратора:
- **Username**: admin (или любое другое имя)
- **Email**: admin@example.com
- **Password**: надежный пароль
- **Role**: owner (обязательно!)

### Создание настроек зарплат по умолчанию
```cmd
python manage.py create_default_salary_config --assign-all
```

### Сбор статических файлов
```cmd
python manage.py collectstatic --noinput
```

## Шаг 7: Запуск сервера разработки

### Запуск Django сервера
```cmd
python manage.py runserver 0.0.0.0:8000
```

**Важно**: `0.0.0.0:8000` позволяет подключаться к серверу удаленно

### Проверка работы
Откройте браузер и перейдите по адресу:
- Локально: `http://localhost:8000`
- Удаленно: `http://IP_АДРЕС_КОМПЬЮТЕРА:8000`

## Шаг 8: Настройка сетевого доступа

### Определение IP-адреса компьютера
```cmd
ipconfig
```
Найдите IPv4-адрес вашего сетевого адаптера (обычно начинается с 192.168.x.x)

### Настройка брандмауэра Windows

#### Метод 1: Через интерфейс
1. Откройте "Панель управления" → "Система и безопасность" → "Брандмауэр Защитника Windows"
2. Нажмите "Дополнительные параметры"
3. Выберите "Правила для входящих подключений"
4. Нажмите "Создать правило..."
5. Выберите "Порт" → "Далее"
6. Выберите "TCP" и укажите порт "8000" → "Далее"
7. Выберите "Разрешить подключение" → "Далее"
8. Отметьте все профили → "Далее"
9. Введите имя правила "Django CRM" → "Готово"

#### Метод 2: Через командную строку (запустите cmd как администратор)
```cmd
netsh advfirewall firewall add rule name="Django CRM" dir=in action=allow protocol=TCP localport=8000
```

## Шаг 9: Создание скриптов для запуска

### Создание bat-файла для запуска
Создайте файл `start_crm.bat` в папке проекта:

```batch
@echo off
echo Запуск CRM системы...
cd /d C:\CRM\crm-project
call venv\Scripts\activate
echo Виртуальное окружение активировано
python manage.py runserver 0.0.0.0:8000
pause
```

### Создание bat-файла для остановки
Создайте файл `stop_crm.bat`:

```batch
@echo off
echo Остановка CRM системы...
taskkill /f /im python.exe
echo CRM система остановлена
pause
```

## Шаг 10: Настройка автозапуска (опционально)

### Создание службы Windows

Создайте файл `install_service.bat` (запускать как администратор):

```batch
@echo off
echo Установка CRM как службы Windows...

sc create "CRM Service" binpath= "C:\CRM\crm-project\venv\Scripts\python.exe C:\CRM\crm-project\manage.py runserver 0.0.0.0:8000" start= auto
sc description "CRM Service" "CRM система для кондиционеров"

echo Служба установлена. Запуск службы...
sc start "CRM Service"

pause
```

### Удаление службы (если нужно)
```batch
sc stop "CRM Service"
sc delete "CRM Service"
```

## Шаг 11: Первоначальная настройка

### Доступ к системе
1. Откройте браузер
2. Перейдите по адресу `http://IP_АДРЕС:8000`
3. Войдите под созданным суперпользователем

### Заполнение начальных данных
1. **Перейдите в админку**: `http://IP_АДРЕС:8000/admin`
2. **Создайте услуги**:
   - Кондиционеры (категория: conditioner)
   - Монтаж (категория: installation)
   - Демонтаж (категория: dismantling)
   - Обслуживание (категория: maintenance)
   - Доп. услуги (категория: additional)

3. **Создайте пользователей**:
   - Менеджеров (role: manager)
   - Монтажников (role: installer)

## Шаг 12: Подключение клиентов

### Для пользователей в той же сети
Просто откройте браузер и перейдите по адресу:
```
http://IP_АДРЕС_СЕРВЕРА:8000
```

### Для удаленного доступа через интернет

#### Вариант 1: Переброс портов на роутере
1. Войдите в админку роутера (обычно 192.168.1.1)
2. Найдите раздел "Port Forwarding" или "Проброс портов"
3. Создайте правило:
   - Внешний порт: 8000
   - Внутренний IP: IP вашего компьютера
   - Внутренний порт: 8000
   - Протокол: TCP

#### Вариант 2: Использование ngrok (проще)
1. Скачайте ngrok с [ngrok.com](https://ngrok.com/)
2. Распакуйте в папку проекта
3. Запустите:
```cmd
ngrok http 8000
```
4. Используйте предоставленный URL для доступа

## Обслуживание системы

### Ежедневный запуск
1. Дважды кликните на `start_crm.bat`
2. Дождитесь сообщения о запуске сервера
3. Система доступна по адресу `http://IP:8000`

### Остановка системы
1. В окне с запущенным сервером нажмите `Ctrl+C`
2. Или дважды кликните на `stop_crm.bat`

### Обновление проекта
```cmd
cd C:\CRM\crm-project
git pull origin main
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

### Резервное копирование
Регулярно копируйте файл базы данных:
```cmd
copy C:\CRM\crm-project\db.sqlite3 C:\CRM\backups\db_backup_%date%.sqlite3
```

## Решение проблем

### Проблема: "Python не найден"
**Решение**: Переустановите Python с опцией "Add to PATH"

### Проблема: "Порт уже используется"
**Решение**: 
```cmd
netstat -ano | findstr :8000
taskkill /PID <номер_процесса> /F
```

### Проблема: "Доступ запрещен"
**Решение**: Проверьте настройки брандмауэра и DJANGO_ALLOWED_HOSTS в .env

### Проблема: Медленная работа
**Решение**: 
1. Измените в settings.py: `DEBUG = False`
2. Добавьте в .env: `DJANGO_DEBUG=False`
3. Перезапустите сервер

### Проблема: Не работает из внешней сети
**Решение**:
1. Проверьте настройки роутера
2. Убедитесь, что порт 8000 открыт в брандмауэре
3. Проверьте, что в .env указано `DJANGO_ALLOWED_HOSTS=*`

## Рекомендации по безопасности

### Для продакшена:
1. **Измените DEBUG на False**:
   ```env
   DJANGO_DEBUG=False
   ```

2. **Ограничьте ALLOWED_HOSTS**:
   ```env
   DJANGO_ALLOWED_HOSTS=192.168.1.100,yourdomain.com
   ```

3. **Используйте сложные пароли**

4. **Регулярно создавайте бэкапы**

5. **Обновляйте систему и зависимости**

### Для тестирования:
Можете оставить `DEBUG=True` для удобства разработки.

## Мониторинг

### Просмотр логов
Логи отображаются в консоли, где запущен сервер. Для сохранения в файл:

```cmd
python manage.py runserver 0.0.0.0:8000 > C:\CRM\logs\server.log 2>&1
```

### Проверка состояния
Периодически проверяйте, что сервер отвечает:
```cmd
curl http://localhost:8000
```

---

После выполнения всех шагов ваша CRM система будет доступна для использования! Пользователи смогут подключаться к ней через браузер, используя IP-адрес вашего компьютера.
