# Task Master API

[![CI](https://github.com/ns-backend/task_master/actions/workflows/ci.yml/badge.svg)](https://github.com/ns-backend/task_master/actions/workflows/ci.yml)

RESTful API для маркетплейса услуг, разработанный на Django REST Framework.

Сервис позволяет провайдерам публиковать услуги, а клиентам — находить и бронировать их. Проект включает ролевую модель доступа, управление категориями, жизненный цикл бронирований, JWT-аутентификацию, автоматические тесты и CI.


## Возможности

- регистрация клиентов и провайдеров;
- JWT-аутентификация;
- получение и редактирование собственного профиля;
- просмотр категорий услуг;
- управление категориями администратором;
- создание и управление услугами провайдерами;
- фильтрация, поиск и сортировка услуг;
- создание бронирований клиентами;
- подтверждение и завершение бронирований провайдерами;
- отмена бронирований клиентами;
- Swagger/OpenAPI-документация;
- автоматические тесты permissions и бизнес-логики;
- автоматический запуск проверок через GitHub Actions.


## Роли и права доступа

### Клиент

- просматривает категории и услуги;
- создаёт бронирования;
- видит только собственные бронирования;
- отменяет свои активные бронирования;
- редактирует собственный профиль.

### Провайдер

- создаёт и редактирует собственные услуги;
- не может изменять услуги других провайдеров;
- видит бронирования только для собственных услуг;
- подтверждает ожидающие бронирования;
- завершает подтверждённые бронирования.

### Администратор

- создаёт, изменяет и удаляет категории;
- управляет данными через Django Admin.


## Жизненный цикл бронирования

- `pending → confirmed` — провайдер подтверждает бронирование;
- `confirmed → completed` — провайдер отмечает услугу выполненной;
- `pending → canceled` — клиент отменяет заявку;
- `confirmed → canceled` — клиент отменяет подтверждённую заявку.

Нельзя завершить неподтверждённое бронирование, подтвердить отменённое или отменить завершённое.


## Технологии

- Python 3.12
- Django
- Django REST Framework
- PostgreSQL
- JWT / Simple JWT
- drf-spectacular
- pytest
- pytest-django
- Docker
- Docker Compose
- GitHub Actions
- Gunicorn


## Запуск через Docker

1. **Клонирование репозитория**

```bash
git clone https://github.com/ns-backend/task_master.git
cd task_master
```

2. **Создание файла окружения**

```bash
cp .env.example .env
```

Для PowerShell:

```powershell
Copy-Item .env.example .env
```

3. **Сборка и запуск контейнеров**

```bash
docker compose build
docker compose up -d
```

4. **Применение миграций**

```bash
docker compose exec web python manage.py migrate
```

5. **Создание администратора**

```bash
docker compose exec web python manage.py createsuperuser
```


## Документация API

После запуска проекта Swagger UI доступен по адресу:

```text
http://localhost:8000/api/docs/
```

OpenAPI-схема:

```text
http://localhost:8000/api/schema/
```


## Тесты

Запуск всех тестов внутри контейнера:

```bash
docker compose exec web pytest
```

Подробный вывод:

```bash
docker compose exec web pytest -v
```

Проверка Django:

```bash
docker compose exec web python manage.py check
```

Проверка отсутствующих миграций:

```bash
docker compose exec web python manage.py makemigrations --check --dry-run
```


## Continuous Integration

GitHub Actions автоматически запускает при push и pull request:

- установку зависимостей;
- PostgreSQL;
- Django system checks;
- проверку миграций;
- применение миграций;
- pytest.


## Основные endpoints

| Метод | Endpoint | Описание |
|---|---|---|
| POST | `/api/users/` | Регистрация |
| GET | `/api/users/me/` | Текущий пользователь |
| PATCH | `/api/users/me/` | Обновление профиля |
| POST | `/api/token/` | Получение JWT |
| GET | `/api/categories/` | Список категорий |
| GET | `/api/services/` | Список услуг |
| POST | `/api/services/` | Создание услуги |
| GET | `/api/bookings/` | Доступные пользователю бронирования |
| POST | `/api/bookings/` | Создание бронирования |
| POST | `/api/bookings/{id}/confirm/` | Подтверждение |
| POST | `/api/bookings/{id}/complete/` | Завершение |
| POST | `/api/bookings/{id}/cancel/` | Отмена |


## Переменные окружения

| Переменная | Назначение |
|---|---|
| `SECRET_KEY` | Секретный ключ Django |
| `DEBUG` | Режим отладки |
| `DB_NAME` | Название базы данных |
| `DB_USER` | Пользователь PostgreSQL |
| `DB_PASSWORD` | Пароль PostgreSQL |
| `DB_HOST` | Хост PostgreSQL |
| `DB_PORT` | Порт PostgreSQL |

Для Docker:

```env
DB_HOST=db
```


## Структура проекта

```text
task_master/
├── core/                 # настройки Django
├── services/             # модели и API маркетплейса
│   ├── migrations/
│   ├── tests/
│   ├── models.py
│   ├── permissions.py
│   ├── serializers.py
│   ├── urls.py
│   └── views.py
├── .github/workflows/    # CI
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── pytest.ini
└── requirements.txt


## Планы развития

- уведомления о смене статуса бронирования;
- фоновые задачи через Celery;
- кеширование с Redis;
- раздельные development и production settings;
- production-развёртывание;
- дополнительные ограничения доступности времени бронирования.
```
