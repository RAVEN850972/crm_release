// Base JavaScript для CRM системы
// static/js/base.js

// Глобальные переменные
let currentUser = null;
let sidebarOpen = false;

// Управление сайдбаром
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const mainContent = document.getElementById('mainContent');
    
    if (window.innerWidth <= 1024) {
        // Мобильная версия
        sidebarOpen = !sidebarOpen;
        sidebar.classList.toggle('mobile-open');
        overlay.classList.toggle('active');
    } else {
        // Десктопная версия
        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('sidebar-collapsed');
    }
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    sidebar.classList.remove('mobile-open');
    overlay.classList.remove('active');
    sidebarOpen = false;
}

// Утилиты для работы с датами
const DateUtils = {
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU');
    },
    
    formatDateTime(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('ru-RU');
    },
    
    formatTime(dateString) {
        const date = new Date(dateString);
        return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    },
    
    getRelativeTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffMins < 1) return 'только что';
        if (diffMins < 60) return `${diffMins} мин назад`;
        if (diffHours < 24) return `${diffHours} ч назад`;
        if (diffDays < 7) return `${diffDays} дн назад`;
        
        return this.formatDate(dateString);
    },
    
    formatDateForInput(dateString) {
        const date = new Date(dateString);
        return date.toISOString().split('T')[0];
    },
    
    formatTimeForInput(dateString) {
        const date = new Date(dateString);
        return date.toTimeString().slice(0, 5);
    }
};

// Утилиты для форматирования валют
const CurrencyUtils = {
    format(amount) {
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    },
    
    formatWithoutSymbol(amount) {
        return new Intl.NumberFormat('ru-RU').format(amount);
    },
    
    parse(string) {
        // Парсинг строки валюты обратно в число
        return parseFloat(string.replace(/[^\d.-]/g, ''));
    }
};

// Утилиты для работы с формами
const FormUtils = {
    serialize(form) {
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            // Обработка множественных значений (checkboxes, multiple selects)
            if (data[key]) {
                if (Array.isArray(data[key])) {
                    data[key].push(value);
                } else {
                    data[key] = [data[key], value];
                }
            } else {
                data[key] = value;
            }
        }
        
        return data;
    },
    
    setErrors(form, errors) {
        // Очищаем предыдущие ошибки
        form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
        form.querySelectorAll('.error-message').forEach(el => el.remove());
        
        // Добавляем новые ошибки
        Object.entries(errors).forEach(([field, messages]) => {
            const fieldElement = form.querySelector(`[name="${field}"]`);
            if (fieldElement) {
                fieldElement.classList.add('error');
                
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error-message';
                errorDiv.textContent = Array.isArray(messages) ? messages[0] : messages;
                
                fieldElement.parentNode.appendChild(errorDiv);
            }
        });
    },
    
    clearErrors(form) {
        form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
        form.querySelectorAll('.error-message').forEach(el => el.remove());
    }
};

// Утилиты для работы с таблицами
const TableUtils = {
    makeSort(table) {
        const headers = table.querySelectorAll('th[data-sort]');
        
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => {
                const sortField = header.dataset.sort;
                const currentSort = new URLSearchParams(window.location.search).get('sort');
                
                let newSort = sortField;
                if (currentSort === sortField) {
                    newSort = `-${sortField}`;
                }
                
                const url = new URL(window.location);
                url.searchParams.set('sort', newSort);
                window.location.href = url.toString();
            });
        });
    },
    
    makeSelectable(table) {
        const checkboxes = table.querySelectorAll('input[type="checkbox"][name="selected"]');
        const selectAll = table.querySelector('input[type="checkbox"][name="select_all"]');
        
        if (selectAll) {
            selectAll.addEventListener('change', () => {
                checkboxes.forEach(cb => cb.checked = selectAll.checked);
                updateBulkActions();
            });
        }
        
        checkboxes.forEach(cb => {
            cb.addEventListener('change', updateBulkActions);
        });
        
        function updateBulkActions() {
            const selected = table.querySelectorAll('input[type="checkbox"][name="selected"]:checked');
            const bulkActions = document.getElementById('bulkActions');
            
            if (bulkActions) {
                if (selected.length > 0) {
                    bulkActions.style.display = 'block';
                    bulkActions.querySelector('.selected-count').textContent = selected.length;
                } else {
                    bulkActions.style.display = 'none';
                }
            }
        }
    }
};

// Загрузка и отображение контента
const ContentLoader = {
    show(selector, content) {
        const container = document.querySelector(selector);
        if (container) {
            container.innerHTML = content;
        }
    },
    
    showLoading(selector) {
        this.show(selector, `
            <div class="loading">
                <div class="spinner"></div>
                Загрузка...
            </div>
        `);
    },
    
    showError(selector, message = 'Произошла ошибка') {
        this.show(selector, `
            <div class="error-state">
                <div class="error-icon">⚠️</div>
                <h3>Ошибка</h3>
                <p>${message}</p>
                <button onclick="window.location.reload()" class="btn btn-primary">
                    Обновить страницу
                </button>
            </div>
        `);
    }
};

// Обработка событий при загрузке
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация текущего пользователя
    if (window.currentUser) {
        currentUser = window.currentUser;
    }
    
    // Закрытие сайдбара при изменении размера окна
    window.addEventListener('resize', () => {
        if (window.innerWidth > 1024 && sidebarOpen) {
            closeSidebar();
        }
    });
    
    // Обработка кликов вне сайдбара на мобильных
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 1024 && sidebarOpen) {
            const sidebar = document.getElementById('sidebar');
            const sidebarToggle = document.querySelector('.sidebar-toggle');
            
            if (sidebar && sidebarToggle && 
                !sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                closeSidebar();
            }
        }
    });
    
    // Инициализация таблиц
    document.querySelectorAll('table.sortable').forEach(table => {
        TableUtils.makeSort(table);
    });
    
    document.querySelectorAll('table.selectable').forEach(table => {
        TableUtils.makeSelectable(table);
    });
    
    // Автофокус на первые поля форм
    const firstInput = document.querySelector('form input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"])');
    if (firstInput) {
        setTimeout(() => firstInput.focus(), 100);
    }
});

// Экспорт в глобальную область видимости
window.CRM = window.CRM || {};
Object.assign(window.CRM, {
    DateUtils,
    CurrencyUtils,
    FormUtils,
    TableUtils,
    ContentLoader,
    toggleSidebar,
    closeSidebar
});