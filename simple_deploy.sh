#!/bin/bash

# === НАСТРОЙКИ ===
PROJECT_NAME="crm"
PROJECT_DIR="/opt/$PROJECT_NAME"
GIT_REPO="https://github.com/your-user/your-repo.git" # ← замени на свой
DJANGO_PORT=8000
DJANGO_SUPERUSER_EMAIL="admin@example.com"

echo "👉 Обновление системы..."
sudo apt update && sudo apt upgrade -y

echo "👉 Установка зависимостей..."
sudo apt install python3-pip python3-venv git nginx supervisor -y

echo "👉 Клонирование проекта..."
sudo git clone $GIT_REPO $PROJECT_DIR
cd $PROJECT_DIR

echo "👉 Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "👉 Настройка Django..."

# Если нужно, скопируй .env, но помни — в .env не должно быть настроек PostgreSQL
cp $PROJECT_DIR/.env.example $PROJECT_DIR/.env 2>/dev/null || true

# Здесь автоматически заменим DATABASES в settings.py на SQLite (если в проекте классический settings.py)
SETTINGS_FILE="$PROJECT_DIR/$PROJECT_NAME/settings.py"
if grep -q "DATABASES = " "$SETTINGS_FILE"; then
    echo "👉 Обновляем настройки базы данных на SQLite..."
    sed -i "/DATABASES = {/,+7d" "$SETTINGS_FILE"
    cat >> "$SETTINGS_FILE" <<EOF

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
EOF
fi

export DJANGO_SETTINGS_MODULE=$PROJECT_NAME.settings
export PYTHONPATH=$PROJECT_DIR

echo "👉 Выполнение миграций и сбор статики..."
python manage.py migrate
python manage.py collectstatic --noinput

echo "👉 Создание суперпользователя..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(email='$DJANGO_SUPERUSER_EMAIL').exists() or User.objects.create_superuser('admin', '$DJANGO_SUPERUSER_EMAIL', 'adminpass123')" | python manage.py shell

echo "👉 Настройка Gunicorn + Supervisor..."
sudo tee /etc/supervisor/conf.d/$PROJECT_NAME.conf > /dev/null <<EOF
[program:$PROJECT_NAME]
directory=$PROJECT_DIR
command=$PROJECT_DIR/venv/bin/gunicorn $PROJECT_NAME.wsgi:application --bind unix:$PROJECT_DIR/$PROJECT_NAME.sock
autostart=true
autorestart=true
stderr_logfile=/var/log/$PROJECT_NAME.err.log
stdout_logfile=/var/log/$PROJECT_NAME.out.log
user=$USER
environment=DJANGO_SETTINGS_MODULE="$PROJECT_NAME.settings",PYTHONPATH="$PROJECT_DIR"
EOF

sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart $PROJECT_NAME

echo "👉 Настройка nginx..."
sudo tee /etc/nginx/sites-available/$PROJECT_NAME > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location /static/ {
        root $PROJECT_DIR;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$PROJECT_DIR/$PROJECT_NAME.sock;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

echo "✅ УСПЕХ! Django-проект '$PROJECT_NAME' развернут и работает на SQLite."
