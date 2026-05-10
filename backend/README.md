# habithamster backend

## Стек:
   | Tech          | Version       |
   | ------------- | ------------- |
   | Python        | 3.12          |
   | Django        | 6             |
   | PostgreSQL    | 16            |

## Компоненты:
* port - 5432: <strong>PostgreSQL</strong>, основная реляционная БД
* port - 8000: <strong>habithamster-backend</strong>, главное бэкенд приложение

## Работа с зависимостями
#### Установка `dev` зависимостей в окружении
```
pip install -r requirements-dev.txt
```

## Билд и запуск проекта локально
* Из корневой директории  репозитория
* Создаем файл переменных окружения
```
cat ./backend/.environment-example > ./backend/.environment
```
* Билдим и запускаем проект
```bash
make build && make up
```
* Накатываем миграции (инструкция ниже)

## Миграции БД
Из директории backend репозитория
### Создание миграции
```bash
make migrations
```
### Применение
```bash
make migrate
```

