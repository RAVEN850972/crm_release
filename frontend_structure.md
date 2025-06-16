# Структура фронтенда CRM системы для кондиционеров

## Технологический стек

### Основные технологии
- **React 18** с TypeScript
- **Vite** - сборщик и dev-сервер
- **React Router v6** - маршрутизация
- **TanStack Query (React Query)** - управление состоянием сервера
- **Zustand** - локальное состояние
- **Tailwind CSS** - стилизация
- **Headless UI** - компоненты интерфейса
- **React Hook Form** - формы
- **Date-fns** - работа с датами
- **Recharts** - графики и диаграммы

### Дополнительные библиотеки
- **React DnD** - drag & drop для календаря
- **React Big Calendar** - календарь монтажей
- **Leaflet** - карты для маршрутизации
- **React Export Table to Excel** - экспорт данных
- **React Hot Toast** - уведомления

## Структура проекта

```
frontend/
├── public/
├── src/
│   ├── components/          # Переиспользуемые компоненты
│   │   ├── ui/             # Базовые UI компоненты
│   │   ├── forms/          # Формы
│   │   ├── tables/         # Таблицы
│   │   ├── charts/         # Графики
│   │   ├── modals/         # Модальные окна
│   │   └── layout/         # Макет приложения
│   ├── pages/              # Страницы приложения
│   │   ├── auth/           # Авторизация
│   │   ├── dashboard/      # Дашборд
│   │   ├── clients/        # Клиенты
│   │   ├── services/       # Услуги
│   │   ├── orders/         # Заказы
│   │   ├── calendar/       # Календарь
│   │   ├── finance/        # Финансы
│   │   ├── users/          # Пользователи
│   │   └── analytics/      # Аналитика
│   ├── hooks/              # Кастомные хуки
│   ├── services/           # API сервисы
│   ├── stores/             # Zustand хранилища
│   ├── types/              # TypeScript типы
│   ├── utils/              # Утилиты
│   └── constants/          # Константы
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

## Ключевые страницы и компоненты

### 1. Система аутентификации
- **LoginPage** - форма входа с поддержкой ролей
- **AuthGuard** - защита маршрутов по ролям

### 2. Главный дашборд (/)
#### Владелец видит:
- Общая статистика (доходы, расходы, заказы)
- Топ менеджеры и монтажники
- Графики по месяцам
- Последние заказы
- Финансовые показатели

#### Менеджер видит:
- Свои заказы и клиенты
- Статистика продаж
- Календарь монтажей
- Новые лиды

#### Монтажник видит:
- Расписание на сегодня/неделю
- Маршрут дня
- История выполненных работ

### 3. Управление клиентами (/clients)
- **ClientsListPage** - таблица с фильтрами и поиском
- **ClientDetailPage** - карточка клиента + история заказов
- **ClientFormModal** - создание/редактирование
- Статистика по источникам привлечения

### 4. Управление услугами (/services)
- **ServicesListPage** - каталог услуг по категориям
- **ServiceDetailPage** - детали услуги + статистика
- **ServiceFormModal** - создание/редактирование
- Анализ популярности и прибыльности

### 5. Управление заказами (/orders)
- **OrdersListPage** - таблица с продвинутыми фильтрами
- **OrderDetailPage** - детальная карточка заказа
- **OrderFormModal** - создание/редактирование
- **OrderItemsManager** - управление позициями заказа
- Канбан-доска по статусам

### 6. Календарь и планирование (/calendar)
- **CalendarPage** - основной календарь монтажей
- **ScheduleFormModal** - создание/редактирование расписания
- **RouteOptimizationPanel** - оптимизация маршрутов
- **InstallerScheduleView** - расписание конкретного монтажника
- Интеграция с картами для маршрутов

### 7. Финансы (/finance)
- **FinanceDashboard** - финансовая сводка
- **TransactionsPage** - список транзакций
- **SalaryCalculationPage** - расчет зарплат
- **ReportsPage** - финансовые отчеты
- Графики доходов/расходов

### 8. Управление пользователями (/users)
- **UsersListPage** - список сотрудников
- **UserDetailPage** - профиль пользователя
- **UserFormModal** - создание/редактирование
- Управление ролями и правами

### 9. Аналитика (/analytics)
- **AnalyticsDashboard** - комплексная аналитика
- Воронка продаж
- Анализ эффективности менеджеров
- Прогнозирование

## Архитектурные решения

### Управление состоянием
```typescript
// Zustand store для аутентификации
interface AuthStore {
  user: User | null;
  token: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

// React Query для серверного состояния
const useOrders = (filters?: OrderFilters) => {
  return useQuery({
    queryKey: ['orders', filters],
    queryFn: () => ordersApi.getList(filters),
  });
};
```

### Система маршрутизации
```typescript
// Защищенные маршруты по ролям
<Route
  path="/finance"
  element={
    <ProtectedRoute roles={['owner']}>
      <FinancePage />
    </ProtectedRoute>
  }
/>
```

### Адаптивный дизайн
- Mobile-first подход
- Sidebar для десктопа, bottom nav для мобайла
- Адаптивные таблицы и графики
- Touch-friendly календарь

## Ключевые особенности UX/UI

### 1. Умные уведомления
- Toast для быстрых действий
- Push для просрочек и важных событий
- Email/SMS через backend

### 2. Быстрые действия
- Создание заказа в 1 клик из карточки клиента
- Drag & drop в календаре
- Bulk operations в таблицах

### 3. Контекстные меню
- Правый клик для быстрых действий
- Keyboard shortcuts
- Quick search (Cmd+K)

### 4. Офлайн поддержка
- Кэширование критических данных
- Sync при восстановлении соединения
- Уведомления о статусе соединения

### 5. Экспорт и отчеты
- Экспорт любых таблиц в Excel/PDF
- Кастомные отчеты
- Печать документов

## Компонентная архитектура

### Базовые UI компоненты
```typescript
// Button с вариантами
<Button variant="primary" size="lg" loading={isSubmitting}>
  Сохранить
</Button>

// Table с фильтрами и сортировкой
<DataTable
  data={orders}
  columns={orderColumns}
  filters={orderFilters}
  onFilterChange={setFilters}
  exportable
/>
```

### Бизнес компоненты
```typescript
// Карточка клиента
<ClientCard
  client={client}
  showActions
  onEdit={handleEdit}
  onCreateOrder={handleCreateOrder}
/>

// Виджет календаря
<CalendarWidget
  installerFilter={installerFilter}
  onScheduleCreate={handleScheduleCreate}
  optimizeRoutes
/>
```

## Оптимизация производительности

### Code Splitting
- Lazy loading страниц
- Dynamic imports для тяжелых компонентов
- Chunk splitting по функциональности

### Кэширование
- React Query для server state
- LocalStorage для пользовательских настроек
- Service Worker для офлайн поддержки

### Виртуализация
- Виртуализация больших таблиц
- Infinite scroll для списков
- Lazy loading изображений

## Развертывание

### Production Build
- Optimized bundle с Vite
- Gzip compression
- CDN для статических файлов
- Error boundary с reporting

### Monitoring
- Analytics через Google Analytics
- Error tracking через Sentry
- Performance monitoring
- User behavior tracking

Эта архитектура обеспечит современный, производительный и масштабируемый фронтенд для вашей CRM системы.