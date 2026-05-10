# Общая архитектура (3 контейнера)

Система представляет собой веб-приложение для отслеживания привычек, которое состоит из трёх основных частей:

- Backend (API + бизнес-логика)
- UI (интерфейс пользователя)
- База данных

### Схема контейнеров

```
[ User ]
   ↓
[ UI (NiceGUI) ]
   ↓ HTTP
[ Backend (FastAPI) ]
   ↓ SQL
[ Database (SQLite/PostgreSQL) ]
```

## Взаимодействие контейнеров

### Основной сценарий (пример: отметить привычку)

1. Пользователь нажимает "Выполнено" в UI
2. UI отправляет POST /habit-log
3. Backend:
   - валидирует данные
   - сохраняет запись в БД
4. Backend возвращает ответ
5. UI обновляет состояние

### Получение данных для дашборда

1. UI делает GET /dashboard
2. Backend:
   - получает привычки
   - считает статистику
3. возвращает агрегированные данные
4. UI отображает графики


## Backend (FastAPI)

Задачи:
- обработка запросов
- бизнес-логика
- работа с БД
- аналитика

### API (минимальный набор)

#### Auth

POST /auth/register  
POST /auth/login  
GET  /auth/me  

#### Привычки

GET    /habits  
POST   /habits  
PUT    /habits/{id}  
DELETE /habits/{id}  

#### Логи (выполнение)

POST /habit-logs  
GET  /habit-logs?habit_id=  

#### Аналитика

GET /analytics/summary  
GET /analytics/habit/{id}  

Что возвращаем:

- % выполнения
- streak
- статистика по дням

Простой вариант:

- JWT токены
- хранение токена на UI
- проверка в каждом запросе

#### Dashboard

GET /dashboard  

Возвращает:

- список привычек
- статус на сегодня
- краткую статистику


## Диаграммы взаимодействия (Sequence)

Сценарий 1: Отметка привычки

```
User → UI: нажимает "Выполнено"
UI → Backend: POST /habit-logs
Backend → DB: INSERT log
DB → Backend: OK
Backend → UI: success
UI → User: обновленный статус
```

Сценарий 2: Загрузка дашборда
```
User → UI: открывает dashboard
UI → Backend: GET /dashboard
Backend → DB: SELECT habits + logs
Backend → Analytics: расчет метрик
Analytics → Backend: данные
Backend → UI: JSON
UI → User: графики и список привычек
```

Сценарий 3: Аналитика
```
UI → Backend: GET /analytics/summary
Backend → DB: SELECT logs
Backend → Analytics:
    - группировка
    - расчет %
    - streak
Backend → UI: инсайты
```

## Внутренняя архитектура Backend

```
        ┌──────────────┐
        │    API       │
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │   Services   │
        └──────┬───────┘
               ▼
   ┌──────────────┐   ┌──────────────┐
   │  Analytics   │   │ Gamification │
   └──────┬───────┘   └──────┬───────┘
          ▼                  ▼
        ┌──────────────────────┐
        │        Models        │
        └──────────┬───────────┘
                   ▼
               Database
```

### Что где происходит

API  
- принимает запросы  
- валидирует  

Services  
- основная логика (CRUD, сценарии)  

Analytics  
- расчет:  
  - процент выполнения  
  - streak  
  - инсайты  

Gamification  
- XP  
- уровни  
- достижения  

## Диаграмма данных (ER-логика)

```
User
 └── Habit
       ├── HabitLog
       └── HabitTag ── Tag
```

### Связи

- User → Habits (1:N)
- Habit → Logs (1:N)
- Habit ↔ Tags (M:N)

## API — визуальная схема

```
[ UI ]
  │
  ├── /auth/*
  ├── /habits
  ├── /habit-logs
  ├── /analytics/*
  └── /dashboard
```

Поток данных

```
UI → API → Services → DB
                ↓
           Analytics
                ↓
              UI
```

## Потоки данных (Data Flow)

Пример: аналитика

Logs → группировка по датам  
     → расчет выполнения  
     → расчет streak  
     → инсайты  

Пример: геймификация
```
HabitLog created
    ↓
Gamification service
    ↓
+XP
    ↓
проверка достижений
```

## Авторизация (упрощенная схема)

User → UI: login  
UI → Backend: POST /auth/login  
Backend → DB: проверка  
Backend → UI: JWT token  
UI → Backend: запросы с токеном  

## Схема логики аналитики

```
Input: habit_logs

→ группировка по:
    - дате
    - тегам
    - времени

→ расчет:
    - completion rate
    - streak
    - best day/time

→ генерация инсайтов
```