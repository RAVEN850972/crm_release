// UI utilities для Django CRM
// static/js/ui.js

const UI = {
    // Toast уведомления
    showToast(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const iconMap = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        };
        
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${iconMap[type] || iconMap.info}</span>
                <span class="toast-message">${message}</span>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        // Добавляем контейнер если его нет
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        
        container.appendChild(toast);
        
        // Анимация появления
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Автоматическое удаление
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
        
        return toast;
    },

    // Модальные окна
    showModal(content, title = '', options = {}) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content" style="width: ${options.width || 'auto'}; max-width: ${options.maxWidth || '90vw'}">
                <div class="modal-header">
                    <h3 class="modal-title">${title}</h3>
                    <button class="modal-close" onclick="UI.closeModal()">&times;</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                ${options.footer ? `<div class="modal-footer">${options.footer}</div>` : ''}
            </div>
        `;
        
        document.body.appendChild(modal);
        setTimeout(() => modal.classList.add('show'), 10);
        
        // Закрытие по клику на overlay
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                UI.closeModal();
            }
        });
        
        // Закрытие по Escape
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                UI.closeModal();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
        
        return modal;
    },

    closeModal() {
        const modal = document.querySelector('.modal-overlay');
        if (modal) {
            modal.classList.remove('show');
            setTimeout(() => modal.remove(), 300);
        }
    },

    // Confirmation диалоги
    confirm(message, title = 'Подтверждение', options = {}) {
        return new Promise((resolve) => {
            const footer = `
                <button class="btn btn-secondary" onclick="UI.closeModal(); resolve(false)">
                    ${options.cancelText || 'Отмена'}
                </button>
                <button class="btn btn-primary" onclick="UI.closeModal(); resolve(true)">
                    ${options.confirmText || 'Подтвердить'}
                </button>
            `;
            
            const modal = UI.showModal(
                `<p>${message}</p>`,
                title,
                { 
                    footer: footer,
                    width: '400px'
                }
            );
            
            // Добавляем обработчики для кнопок
            const buttons = modal.querySelectorAll('.modal-footer button');
            buttons[0].onclick = () => { UI.closeModal(); resolve(false); };
            buttons[1].onclick = () => { UI.closeModal(); resolve(true); };
        });
    },

    // Loading состояния
    showLoading(element, text = 'Загрузка...') {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (element) {
            element.innerHTML = `
                <div class="loading-state">
                    <div class="spinner"></div>
                    <span>${text}</span>
                </div>
            `;
        }
    },

    hideLoading(element) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (element) {
            const loading = element.querySelector('.loading-state');
            if (loading) {
                loading.remove();
            }
        }
    },

    // Tabs
    initTabs(container) {
        const tabsContainer = typeof container === 'string' ? 
            document.querySelector(container) : container;
        
        if (!tabsContainer) return;
        
        const tabs = tabsContainer.querySelectorAll('.tab-button');
        const panels = tabsContainer.querySelectorAll('.tab-panel');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetId = tab.dataset.tab;
                
                // Деактивируем все табы и панели
                tabs.forEach(t => t.classList.remove('active'));
                panels.forEach(p => p.classList.remove('active'));
                
                // Активируем выбранный таб и панель
                tab.classList.add('active');
                const targetPanel = tabsContainer.querySelector(`#${targetId}`);
                if (targetPanel) {
                    targetPanel.classList.add('active');
                }
            });
        });
    },

    // Dropdown меню
    initDropdowns() {
        document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                const dropdown = toggle.parentElement;
                const menu = dropdown.querySelector('.dropdown-menu');
                
                // Закрываем все другие dropdown
                document.querySelectorAll('.dropdown.open').forEach(d => {
                    if (d !== dropdown) d.classList.remove('open');
                });
                
                dropdown.classList.toggle('open');
            });
        });
        
        // Закрытие при клике вне dropdown
        document.addEventListener('click', () => {
            document.querySelectorAll('.dropdown.open').forEach(d => {
                d.classList.remove('open');
            });
        });
    },

    // Tooltips
    initTooltips() {
        document.querySelectorAll('[data-tooltip]').forEach(element => {
            element.addEventListener('mouseenter', (e) => {
                const tooltip = document.createElement('div');
                tooltip.className = 'tooltip';
                tooltip.textContent = element.dataset.tooltip;
                document.body.appendChild(tooltip);
                
                const rect = element.getBoundingClientRect();
                tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
                tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
                
                element._tooltip = tooltip;
            });
            
            element.addEventListener('mouseleave', () => {
                if (element._tooltip) {
                    element._tooltip.remove();
                    element._tooltip = null;
                }
            });
        });
    },

    // Формы
    handleForm(form, options = {}) {
        if (typeof form === 'string') {
            form = document.querySelector(form);
        }
        
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = form.querySelector('[type="submit"]');
            const originalText = submitBtn?.textContent;
            
            try {
                // Показываем загрузку
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner"></span> Сохранение...';
                }
                
                // Очищаем предыдущие ошибки
                CRM.FormUtils.clearErrors(form);
                
                // Определяем API метод
                const method = form.method.toUpperCase();
                const action = form.action;
                
                let data;
                if (form.enctype === 'multipart/form-data') {
                    data = new FormData(form);
                } else {
                    data = JSON.stringify(CRM.FormUtils.serialize(form));
                }
                
                const response = await CRM.API.request(action, {
                    method,
                    body: data,
                    headers: method !== 'GET' ? { 'X-CSRFToken': CRM.API.getCSRFToken() } : {}
                });
                
                // Обработка успешного ответа
                if (options.onSuccess) {
                    options.onSuccess(response);
                } else {
                    UI.showToast('Данные успешно сохранены', 'success');
                    if (options.redirect) {
                        window.location.href = options.redirect;
                    }
                }
                
            } catch (error) {
                // Обработка ошибок
                if (error.status === 400 && error.errors) {
                    CRM.FormUtils.setErrors(form, error.errors);
                } else {
                    UI.showToast(error.message || 'Произошла ошибка при сохранении', 'error');
                }
                
                if (options.onError) {
                    options.onError(error);
                }
            } finally {
                // Возвращаем кнопку в исходное состояние
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }
            }
        });
    },

    // Async select (поиск с автокомплитом)
    initAsyncSelect(select, apiEndpoint, options = {}) {
        const container = document.createElement('div');
        container.className = 'async-select';
        
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'form-control';
        input.placeholder = options.placeholder || 'Начните вводить для поиска...';
        
        const dropdown = document.createElement('div');
        dropdown.className = 'async-select-dropdown';
        dropdown.style.display = 'none';
        
        container.appendChild(input);
        container.appendChild(dropdown);
        
        select.parentNode.insertBefore(container, select);
        select.style.display = 'none';
        
        const debouncedSearch = CRM.API.helpers.debounce(async (query) => {
            if (query.length < 2) {
                dropdown.style.display = 'none';
                return;
            }
            
            try {
                const response = await CRM.API.request(`${apiEndpoint}?search=${encodeURIComponent(query)}`);
                const items = response.data || response;
                
                dropdown.innerHTML = items.map(item => `
                    <div class="async-select-item" data-value="${item.id}">
                        ${options.formatItem ? options.formatItem(item) : item.name}
                    </div>
                `).join('');
                
                dropdown.style.display = 'block';
                
                // Обработчики клика по элементам
                dropdown.querySelectorAll('.async-select-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const value = item.dataset.value;
                        const text = item.textContent;
                        
                        input.value = text;
                        select.value = value;
                        dropdown.style.display = 'none';
                        
                        if (options.onSelect) {
                            options.onSelect(value, text);
                        }
                    });
                });
                
            } catch (error) {
                dropdown.innerHTML = '<div class="async-select-error">Ошибка загрузки</div>';
                dropdown.style.display = 'block';
            }
        }, 300);
        
        input.addEventListener('input', (e) => {
            debouncedSearch(e.target.value);
        });
        
        // Закрытие при клике вне элемента
        document.addEventListener('click', (e) => {
            if (!container.contains(e.target)) {
                dropdown.style.display = 'none';
            }
        });
    },

    // Bulk actions для таблиц
    initBulkActions(table) {
        const tableElement = typeof table === 'string' ? document.querySelector(table) : table;
        if (!tableElement) return;
        
        const selectAllCheckbox = tableElement.querySelector('input[name="select_all"]');
        const itemCheckboxes = tableElement.querySelectorAll('input[name="selected"]');
        const bulkActionsPanel = document.querySelector('.bulk-actions');
        
        function updateBulkActions() {
            const selectedItems = tableElement.querySelectorAll('input[name="selected"]:checked');
            const selectedCount = selectedItems.length;
            
            if (bulkActionsPanel) {
                if (selectedCount > 0) {
                    bulkActionsPanel.style.display = 'flex';
                    bulkActionsPanel.querySelector('.selected-count').textContent = selectedCount;
                } else {
                    bulkActionsPanel.style.display = 'none';
                }
            }
            
            // Обновляем состояние "выбрать все"
            if (selectAllCheckbox) {
                selectAllCheckbox.indeterminate = selectedCount > 0 && selectedCount < itemCheckboxes.length;
                selectAllCheckbox.checked = selectedCount === itemCheckboxes.length;
            }
        }
        
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', () => {
                itemCheckboxes.forEach(checkbox => {
                    checkbox.checked = selectAllCheckbox.checked;
                });
                updateBulkActions();
            });
        }
        
        itemCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', updateBulkActions);
        });
        
        return {
            getSelectedIds: () => {
                return Array.from(tableElement.querySelectorAll('input[name="selected"]:checked'))
                    .map(cb => cb.value);
            },
            clearSelection: () => {
                itemCheckboxes.forEach(cb => cb.checked = false);
                if (selectAllCheckbox) selectAllCheckbox.checked = false;
                updateBulkActions();
            }
        };
    }
};

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', () => {
    UI.initDropdowns();
    UI.initTooltips();
    
    // Инициализация всех табов на странице
    document.querySelectorAll('.tabs').forEach(tabs => {
        UI.initTabs(tabs);
    });
    
    // Инициализация всех форм с data-ajax
    document.querySelectorAll('form[data-ajax]').forEach(form => {
        UI.handleForm(form);
    });
    
    // Инициализация bulk actions для всех таблиц
    document.querySelectorAll('table.bulk-actions').forEach(table => {
        UI.initBulkActions(table);
    });
});

// Добавляем в глобальную область
window.CRM = window.CRM || {};
window.CRM.UI = UI;