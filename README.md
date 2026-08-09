# Task Master API

[![CI](https://github.com/ns-backend/task_master/actions/workflows/ci.yml/badge.svg)](https://github.com/ns-backend/task_master/actions/workflows/ci.yml)

REST API для маркетплейса услуг на Django REST Framework.

Task Master позволяет провайдерам публиковать услуги, а клиентам — находить и бронировать их. Проект включает ролевую модель доступа, жизненный цикл бронирований, JWT-аутентификацию, фильтрацию и поиск, защиту бизнес-операций от конкурентных изменений, автоматические тесты, статический анализ и CI.

## Возможности

- регистрация клиентов и провайдеров;
- JWT-аутентификация;
- получение и редактирование собственного профиля;
- публичный просмотр категорий и услуг;
- управление категориями администратором;
- создание и управление собственными услугами провайдерами;
- фильтрация услуг по категории и цене;
- поиск по названию и описанию;
- сортировка по цене и дате создания;
- создание бронирований клиентами;
- подтверждение и завершение бронирований провайдерами;
- отмена активных бронирований клиентами;
- Swagger/OpenAPI-документация;
- тестирование API, permissions, моделей и бизнес-логики;
- linting и formatting через Ruff;
- автоматические проверки через pre-commit;
- CI через GitHub Actions.

## Роли и права доступа

### Клиент

Клиент может:

- просматривать категории и услуги;
- создавать бронирования;
- видеть только собственные бронирования;
- отменять собственные активные бронирования;
- получать и редактировать собственный профиль.

Клиент не может:

- создавать и изменять услуги;
- управлять категориями;
- изменять статус бронирования напрямую;
- бронировать собственную услугу.

### Провайдер

Провайдер может:

- просматривать категории и услуги;
- создавать услуги;
- редактировать и удалять только собственные услуги;
- видеть бронирования только для собственных услуг;
- подтверждать ожидающие бронирования;
- завершать подтверждённые бронирования.

Провайдер не может создавать бронирования как клиент.

### Администратор

Администратор может:

- создавать категории;
- изменять категории;
- удалять категории;
- управлять данными через Django Admin.

Чтение категорий остаётся публичным.

## Жизненный цикл бронирования

Бронирование создаётся со статусом:

```text
pending
```

Поддерживаются следующие переходы:

```text
pending   → confirmed
confirmed → completed

pending   → canceled
confirmed → canceled
```

Правила:

- `pending → confirmed` выполняет провайдер услуги;
- `confirmed → completed` выполняет провайдер услуги;
- `pending → canceled` выполняет клиент;
- `confirmed → canceled` выполняет клиент.

Недопустимые переходы отклоняются API.

Например:

- нельзя завершить неподтверждённое бронирование;
- нельзя подтвердить отменённое бронирование;
- нельзя отменить завершённое бронирование.

Статус нельзя произвольно изменить через обычный `PATCH`: переходы выполняются через отдельные действия API.

## Архитектура

Проект разделяет HTTP-слой и бизнес-логику.

### ViewSets

ViewSet отвечает за:

- получение HTTP-запроса;
- выбор доступного пользователю queryset;
- permissions;
- сериализацию запроса и ответа;
- вызов бизнес-операции.

### Serializers

Сериализаторы отвечают за:

- структуру входных и выходных данных;
- проверку пользовательского ввода;
- read-only/write-only ограничения;
- API-level validation.

Для услуг используются отдельные сериализаторы чтения и записи.

`ServiceReadSerializer` возвращает подробное представление услуги, а `ServiceWriteSerializer` принимает только поля, которые пользователь действительно может изменять.

### Booking service layer

Изменение состояния бронирования вынесено из ViewSet в:

```text
services/booking_services.py
```

В сервисном слое находятся операции:

```python
confirm_booking(...)
complete_booking(...)
cancel_booking(...)
```

Так бизнес-правила переходов статуса не зависят напрямую от HTTP ViewSet и могут тестироваться отдельно.

## Транзакции и защита от race conditions

Изменение статуса бронирования выполняется внутри:

```python
transaction.atomic
```

Перед изменением запись блокируется:

```python
select_for_update()
```

Это предотвращает ситуацию, когда два конкурентных запроса одновременно читают один старый статус и оба пытаются выполнить переход состояния.

Упрощённо:

```text
Request A ─┐
           ├─ пытаются изменить одно Booking
Request B ─┘

select_for_update()
        ↓
один запрос получает блокировку
        ↓
проверяет актуальный статус
        ↓
изменяет запись
        ↓
commit
        ↓
второй запрос продолжает уже с актуальным состоянием
```

Блокировка применяется внутри транзакции и действует до её завершения.

## Контроль доступа к объектам

Для услуг используется object-level permission.

Публичные операции чтения доступны всем:

```text
GET /api/services/
GET /api/services/{id}/
```

Изменять или удалять услугу может только её провайдер.

Попытка другого провайдера изменить существующую публичную услугу возвращает:

```text
403 Forbidden
```

Для бронирований используется другой подход.

Queryset сразу ограничивается текущим пользователем:

- клиент получает только собственные бронирования;
- провайдер получает только бронирования собственных услуг.

Поэтому недоступное пользователю бронирование не попадает в queryset и возвращает:

```text
404 Not Found
```

Так API не раскрывает наличие чужих бронирований.

## API contract профиля

Роль можно выбрать во время регистрации:

```json
{
  "is_provider": true
}
```

После регистрации изменить роль через endpoint собственного профиля нельзя.

Разрешённые для изменения поля:

```text
email
phone_number
```

Попытка отправить запрещённое поле, например:

```json
{
  "is_provider": true
}
```

возвращает:

```text
400 Bad Request
```

API не игнорирует такие поля молча, а явно сообщает об ошибке.

## Валидация и ограничения базы данных

Цена услуги должна быть больше нуля.

Это правило проверяется на нескольких уровнях:

- serializer validation;
- model validation;
- PostgreSQL/Django `CheckConstraint`.

Ограничение базы данных:

```text
service_price_gt_zero
```

Так корректность данных не зависит только от того, через какой слой приложения была создана запись.

Для бронирований также проверяется:

- дата должна находиться в будущем;
- пользователь не может забронировать собственную услугу;
- провайдер не может создавать бронирования как клиент.

## Оптимизация запросов

Для связанных объектов используются оптимизированные queryset.

Например, услуги загружаются вместе с:

```text
category
provider
```

через:

```python
select_related()
```

Бронирования загружаются вместе с:

```text
client
service
service.provider
```

Это уменьшает количество дополнительных SQL-запросов при сериализации данных.

В тестах также есть проверка количества запросов для списка услуг, чтобы защититься от появления N+1 problem при дальнейших изменениях проекта.

## Фильтрация, поиск и сортировка

Для списка услуг поддерживается фильтрация через `django-filter`.

### Категория

```text
GET /api/services/?category=1
```

### Минимальная цена

```text
GET /api/services/?price__gte=100
```

### Максимальная цена

```text
GET /api/services/?price__lte=500
```

### Поиск

Поиск выполняется по названию и описанию:

```text
GET /api/services/?search=ремонт
```

### Сортировка

По цене:

```text
GET /api/services/?ordering=price
GET /api/services/?ordering=-price
```

По дате создания:

```text
GET /api/services/?ordering=created_at
GET /api/services/?ordering=-created_at
```

По умолчанию новые услуги отображаются первыми.

## Основные endpoints

| Метод | Endpoint | Описание |
|---|---|---|
| POST | `/api/users/` | Регистрация пользователя |
| GET | `/api/users/me/` | Получение собственного профиля |
| PATCH | `/api/users/me/` | Обновление собственного профиля |
| POST | `/api/token/` | Получение JWT |
| POST | `/api/token/refresh/` | Обновление JWT |
| GET | `/api/categories/` | Список категорий |
| POST | `/api/categories/` | Создание категории администратором |
| GET | `/api/services/` | Список услуг |
| GET | `/api/services/{id}/` | Получение услуги |
| POST | `/api/services/` | Создание услуги провайдером |
| PATCH | `/api/services/{id}/` | Изменение собственной услуги |
| DELETE | `/api/services/{id}/` | Удаление собственной услуги |
| GET | `/api/bookings/` | Доступные пользователю бронирования |
| GET | `/api/bookings/{id}/` | Получение бронирования |
| POST | `/api/bookings/` | Создание бронирования |
| POST | `/api/bookings/{id}/confirm/` | Подтверждение бронирования |
| POST | `/api/bookings/{id}/complete/` | Завершение бронирования |
| POST | `/api/bookings/{id}/cancel/` | Отмена бронирования |

Полный API contract доступен через Swagger после запуска приложения.

## Технологии

### Backend

- Python 3.12
- Django 6
- Django REST Framework
- django-filter
- Simple JWT
- drf-spectacular

### Database

- PostgreSQL 16
- psycopg2

### Testing and code quality

- pytest
- pytest-django
- Ruff
- pre-commit

### Infrastructure

- Docker
- Docker Compose
- Gunicorn
- GitHub Actions

## Зависимости

Зависимости разделены по назначению:

```text
requirements/
├── base.txt
├── dev.txt
└── production.txt
```

### `base.txt`

Основные runtime-зависимости приложения:

- Django;
- Django REST Framework;
- django-filter;
- Simple JWT;
- drf-spectacular;
- PostgreSQL driver;
- python-dotenv.

### `dev.txt`

Подключает `base.txt` и добавляет инструменты разработки:

- pytest;
- pytest-django;
- Ruff;
- pre-commit.

### `production.txt`

Подключает `base.txt` и добавляет:

- Gunicorn.

Корневой:

```text
requirements.txt
```

подключает development-набор для локальной разработки и development Docker environment.

## Запуск через Docker

### 1. Клонирование репозитория

```bash
git clone https://github.com/ns-backend/task_master.git
cd task_master
```

### 2. Создание `.env`

Linux/macOS:

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

После копирования при необходимости измените значения переменных.

### 3. Сборка образов

```bash
docker compose build
```

### 4. Запуск контейнеров

```bash
docker compose up -d
```

Проверить состояние:

```bash
docker compose ps
```

### 5. Применение миграций

```bash
docker compose exec web python manage.py migrate
```

### 6. Создание администратора

```bash
docker compose exec web python manage.py createsuperuser
```

После запуска API доступен по адресу:

```text
http://localhost:8000/
```

## Переменные окружения

Пример находится в:

```text
.env.example
```

Используются следующие переменные:

| Переменная | Назначение |
|---|---|
| `SECRET_KEY` | Секретный ключ Django |
| `DEBUG` | Режим отладки |
| `ALLOWED_HOSTS` | Разрешённые hostnames |
| `DB_NAME` | Название PostgreSQL database |
| `DB_USER` | Пользователь PostgreSQL |
| `DB_PASSWORD` | Пароль PostgreSQL |
| `DB_HOST` | Хост PostgreSQL |
| `DB_PORT` | Порт PostgreSQL |

Для запуска через Docker Compose:

```env
DB_HOST=db
```

Обязательные параметры приложения и базы данных проверяются при старте. Если необходимая переменная окружения отсутствует, приложение завершается с явной ошибкой конфигурации.

## API-документация

Swagger UI:

```text
http://localhost:8000/api/docs/
```

OpenAPI schema:

```text
http://localhost:8000/api/schema/
```

## Тестирование

Запуск всех тестов внутри Docker:

```bash
docker compose exec web pytest
```

Краткий вывод:

```bash
docker compose exec web pytest -q
```

Подробный:

```bash
docker compose exec web pytest -v
```

Тесты покрывают:

- регистрацию и профиль пользователя;
- permissions;
- работу категорий;
- CRUD услуг;
- фильтрацию;
- поиск;
- сортировку;
- количество SQL-запросов;
- создание бронирований;
- видимость бронирований;
- переходы статусов;
- бизнес-логику booking service layer;
- model validation;
- database constraints.

## Code quality

Проект использует Ruff для linting и formatting.

Проверка:

```bash
ruff check .
```

Проверка форматирования:

```bash
ruff format --check .
```

Автоматическое форматирование:

```bash
ruff format .
```

Исправление доступных lint-проблем:

```bash
ruff check . --fix
```

## Pre-commit

Для локальной установки hooks:

```bash
pre-commit install
```

Запуск для всех файлов:

```bash
pre-commit run --all-files
```

Hooks проверяют в том числе:

- Ruff lint;
- Ruff formatting;
- YAML;
- TOML;
- trailing whitespace;
- перенос строки в конце файлов;
- merge conflict markers;
- случайно добавленные большие файлы;
- private keys.

## Проверка проекта перед коммитом

Рекомендуемый полный набор проверок:

```bash
ruff check .
ruff format --check .
pre-commit run --all-files
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose exec web pytest -q
```

## Continuous Integration

GitHub Actions запускается при:

```text
push
pull_request
```

CI поднимает PostgreSQL 16 и выполняет:

1. установку development-зависимостей;
2. `ruff check .`;
3. `ruff format --check .`;
4. Django system check;
5. проверку отсутствия несозданных миграций;
6. применение миграций;
7. полный запуск pytest.

Pull Request считается готовым к merge после успешного прохождения CI.

## Docker

Dockerfile использует multi-stage build.

На первом этапе:

- создаётся отдельное virtual environment;
- устанавливаются Python-зависимости.

На втором этапе:

- используется новый минимальный Python image;
- копируется готовое virtual environment;
- исходный код запускается от непривилегированного пользователя `appuser`.

Dockerfile содержит production-команду запуска через Gunicorn.

При запуске через `docker-compose.yml` она переопределяется development-командой:

```text
python manage.py runserver 0.0.0.0:8000
```

Это позволяет использовать один Dockerfile как основу для development и production-oriented runtime.

## Структура проекта

```text
task_master/
├── core/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── services/
│   ├── migrations/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_booking_services.py
│   │   ├── test_bookings.py
│   │   ├── test_categories.py
│   │   ├── test_models.py
│   │   ├── test_services.py
│   │   └── test_users.py
│   │
│   ├── admin.py
│   ├── booking_services.py
│   ├── models.py
│   ├── permissions.py
│   ├── serializers.py
│   ├── urls.py
│   └── views.py
│
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── production.txt
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .env.example
├── .pre-commit-config.yaml
├── .dockerignore
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── pyproject.toml
├── pytest.ini
├── requirements.txt
└── README.md
```

## Ключевые технические решения

В проекте сознательно применены следующие подходы:

- business logic переходов бронирования вынесена из ViewSet в service layer;
- критические изменения состояния выполняются внутри database transaction;
- `select_for_update()` защищает booking transitions от race conditions;
- queryset ограничивает видимость чужих бронирований;
- object-level permissions защищают изменение чужих услуг;
- read/write serializers разделены для разных API-сценариев;
- API отклоняет недопустимые поля профиля явным `400 Bad Request`;
- `CheckConstraint` защищает целостность цены услуги на уровне базы данных;
- `select_related()` уменьшает количество SQL-запросов;
- query-count test защищает список услуг от N+1 regression;
- зависимости разделены на runtime, development и production;
- Ruff и pre-commit поддерживают единый стиль кода;
- GitHub Actions автоматически проверяет код перед merge.

## Планы развития

Возможные следующие этапы развития проекта:

- ограничения пересекающихся бронирований по времени;
- уведомления о смене статуса бронирования;
- фоновые задачи через Celery;
- Redis для кеширования и background infrastructure;
- отдельные Django settings для development и production;
- production deployment;
- расширение API monitoring и logging.
