// API utilities для Django CRM
// static/js/api.js

const API = {
    baseURL: '/api',
    
    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            credentials: 'include', // Для session authentication
            ...options
        };

        // Добавляем CSRF токен для изменяющих запросов
        if (options.method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method.toUpperCase())) {
            const csrfToken = this.getCSRFToken();
            if (csrfToken) {
                config.headers['X-CSRFToken'] = csrfToken;
            }
        }

        try {
            const response = await fetch(url, config);
            
            // Обработка разных типов контента
            let data;
            const contentType = response.headers.get('content-type');
            
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                data = await response.text();
            }
            
            if (!response.ok) {
                throw {
                    status: response.status,
                    statusText: response.statusText,
                    message: data.error || data.detail || 'Произошла ошибка',
                    errors: data.errors || {},
                    data: data
                };
            }
            
            return data;
        } catch (error) {
            if (error.name === 'TypeError') {
                throw {
                    status: 0,
                    message: 'Ошибка подключения к серверу',
                    errors: {}
                };
            }
            throw error;
        }
    },

    getCSRFToken() {
        // Сначала пытаемся получить из window
        if (window.csrfToken) {
            return window.csrfToken;
        }
        
        // Затем из cookie
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        
        // Последняя попытка - из мета тега
        if (!cookieValue) {
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            if (csrfMeta) {
                cookieValue = csrfMeta.getAttribute('content');
            }
        }
        
        return cookieValue;
    },

    // Методы для работы с пользователями
    user: {
        async getCurrent() {
            return API.request('/users/me/');
        },
        
        async list(params = {}) {
            const query = new URLSearchParams(params).toString();
            return API.request(`/users/?${query}`);
        },
        
        async create(data) {
            return API.request('/users/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        },
        
        async update(id, data) {
            return API.request(`/users/${id}/`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        },
        
        async delete(id) {
            return API.request(`/users/${id}/`, {
                method: 'DELETE'
            });
        }
    },

    // Методы для работы с клиентами
    clients: {
        async list(params = {}) {
            const query = new URLSearchParams(params).toString();
            return API.request(`/clients/?${query}`);
        },
        
        async get(id) {
            return API.request(`/clients/${id}/`);
        },
        
        async create(data) {
            return API.request('/clients/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        },
        
        async update(id, data) {
            return API.request(`/clients/${id}/`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        },
        
        async delete(id) {
            return API.request(`/clients/${id}/`, {
                method: 'DELETE'
            });
        }
    },

    // Методы для работы с заказами
    orders: {
        async list(params = {}) {
            const query = new URLSearchParams(params).toString();
            return API.request(`/orders/?${query}`);
        },
        
        async get(id) {
            return API.request(`/orders/${id}/`);
        },
        
        async create(data) {
            return API.request('/orders/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        },
        
        async update(id, data) {
            return API.request(`/orders/${id}/`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        },
        
        async delete(id) {
            return API.request(`/orders/${id}/`, {
                method: 'DELETE'
            });
        },
        
        async addItem(orderId, itemData) {
            return API.request(`/modal/order/${orderId}/items/`, {
                method: 'POST',
                body: JSON.stringify(itemData)
            });
        },
        
        async removeItem(orderId, itemId) {
            return API.request(`/modal/order/${orderId}/items/${itemId}/`, {
                method: 'DELETE'
            });
        }
    },

    // Методы для работы с услугами
    services: {
        async list(params = {}) {
            const query = new URLSearchParams(params).toString();
            return API.request(`/services/?${query}`);
        },
        
        async get(id) {
            return API.request(`/services/${id}/`);
        },
        
        async create(data) {
            return API.request('/services/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        },
        
        async update(id, data) {
            return API.request(`/services/${id}/`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        },
        
        async delete(id) {
            return API.request(`/services/${id}/`, {
                method: 'DELETE'
            });
        }
    },

    // Методы для работы с календарем
    calendar: {
        async getSchedules(params = {}) {
            const query = new URLSearchParams(params).toString();
            return API.request(`/calendar/?${query}`);
        },
        
        async createSchedule(data) {
            return API.request('/calendar/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        },
        
        async updateSchedule(id, data) {
            return API.request(`/calendar/schedule/${id}/`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        },
        
        async deleteSchedule(id) {
            return API.request(`/calendar/schedule/${id}/`, {
                method: 'DELETE'
            });
        },
        
        async startWork(scheduleId) {
            return API.request(`/calendar/schedule/${scheduleId}/start/`, {
                method: 'POST'
            });
        },
        
        async completeWork(scheduleId) {
            return API.request(`/calendar/schedule/${scheduleId}/complete/`, {
                method: 'POST'
            });
        }
    },

    // Методы для работы с финансами
    finance: {
        async getBalance() {
            return API.request('/finance/balance/');
        },
        
        async getTransactions(params = {}) {
            const query = new URLSearchParams(params).toString();
            return API.request(`/transactions/?${query}`);
        },
        
        async createTransaction(data) {
            return API.request('/transactions/', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }
    },

    // Методы для дашборда
    dashboard: {
        async getStats() {
            return API.request('/dashboard/stats/');
        }
    },

    // Поиск
    async search(query, params = {}) {
        const searchParams = new URLSearchParams({
            q: query,
            ...params
        }).toString();
        return API.request(`/search/?${searchParams}`);
    },

    // Экспорт данных
    export: {
        async clients(params = {}) {
            const query = new URLSearchParams(params).toString();
            return API.request(`/export/clients/?${query}`, {
                headers: {
                    'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                }
            });
        },
        
        async orders(params = {}) {
            const query = new URLSearchParams(params).toString();
            return API.request(`/export/orders/?${query}`, {
                headers: {
                    'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                }
            });
        },
        
        async finance(params = {}) {
            const query = new URLSearchParams(params).toString();
            return API.request(`/export/finance/?${query}`, {
                headers: {
                    'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                }
            });
        }
    },

    // Модальные формы
    modal: {
        async getClientForm(id = null) {
            const endpoint = id ? `/modal/client/${id}/` : '/modal/client/';
            return API.request(endpoint);
        },
        
        async saveClient(data, id = null) {
            const endpoint = id ? `/modal/client/${id}/` : '/modal/client/';
            const method = id ? 'PUT' : 'POST';
            return API.request(endpoint, {
                method,
                body: JSON.stringify(data)
            });
        },
        
        async getOrderForm(id = null) {
            const endpoint = id ? `/modal/order/${id}/` : '/modal/order/';
            return API.request(endpoint);
        },
        
        async saveOrder(data, id = null) {
            const endpoint = id ? `/modal/order/${id}/` : '/modal/order/';
            const method = id ? 'PUT' : 'POST';
            return API.request(endpoint, {
                method,
                body: JSON.stringify(data)
            });
        }
    },

    // Обработка файлов
    upload: {
        async file(file, endpoint = '/upload/') {
            const formData = new FormData();
            formData.append('file', file);
            
            return API.request(endpoint, {
                method: 'POST',
                headers: {
                    // Убираем Content-Type для FormData
                    'X-CSRFToken': API.getCSRFToken()
                },
                body: formData
            });
        }
    }
};

// Обработчики ошибок
API.handleError = function(error, options = {}) {
    console.error('API Error:', error);
    
    if (error.status === 401) {
        // Неавторизованный доступ - перенаправляем на логин
        if (options.redirectOnAuth !== false) {
            window.location.href = '/user_accounts/login/';
        }
        return;
    }
    
    if (error.status === 403) {
        // Недостаточно прав
        CRM.UI.showToast('У вас недостаточно прав для выполнения этого действия', 'error');
        return;
    }
    
    if (error.status === 404) {
        // Не найдено
        CRM.UI.showToast('Запрашиваемый ресурс не найден', 'error');
        return;
    }
    
    if (error.status === 400) {
        // Ошибка валидации
        if (error.errors && options.form) {
            CRM.FormUtils.setErrors(options.form, error.errors);
        } else {
            CRM.UI.showToast(error.message || 'Ошибка валидации данных', 'error');
        }
        return;
    }
    
    if (error.status === 0) {
        // Ошибка сети
        CRM.UI.showToast('Ошибка подключения к серверу. Проверьте интернет-соединение.', 'error');
        return;
    }
    
    // Общая ошибка
    CRM.UI.showToast(error.message || 'Произошла неизвестная ошибка', 'error');
};

// Хелперы для работы с API
API.helpers = {
    // Загрузка данных с индикатором
    async loadWithIndicator(apiCall, loadingSelector) {
        try {
            if (loadingSelector) {
                CRM.ContentLoader.showLoading(loadingSelector);
            }
            
            const result = await apiCall();
            return result;
        } catch (error) {
            if (loadingSelector) {
                CRM.ContentLoader.showError(loadingSelector, error.message);
            }
            throw error;
        }
    },
    
    // Обработка пагинации
    handlePagination(response, container, renderFunction) {
        if (response.data) {
            renderFunction(response.data);
        }
        
        // Обновляем пагинацию
        const pagination = container.querySelector('.pagination');
        if (pagination && response.meta) {
            this.updatePagination(pagination, response.meta);
        }
    },
    
    updatePagination(paginationElement, meta) {
        const { count, next, previous } = meta;
        const currentPage = new URLSearchParams(window.location.search).get('page') || 1;
        const totalPages = Math.ceil(count / 20); // Предполагаем 20 элементов на страницу
        
        let paginationHTML = '';
        
        // Предыдущая страница
        if (previous) {
            paginationHTML += `<a href="?page=${parseInt(currentPage) - 1}" class="pagination-btn">‹ Назад</a>`;
        }
        
        // Номера страниц
        for (let i = 1; i <= totalPages; i++) {
            if (i == currentPage) {
                paginationHTML += `<span class="pagination-btn active">${i}</span>`;
            } else {
                paginationHTML += `<a href="?page=${i}" class="pagination-btn">${i}</a>`;
            }
        }
        
        // Следующая страница
        if (next) {
            paginationHTML += `<a href="?page=${parseInt(currentPage) + 1}" class="pagination-btn">Далее ›</a>`;
        }
        
        paginationElement.innerHTML = paginationHTML;
    },
    
    // Debounce для поиска
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// Добавляем в глобальную область
window.CRM = window.CRM || {};
window.CRM.API = API;