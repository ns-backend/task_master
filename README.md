# Task Master API

[![CI](https://github.com/ns-backend/task_master/actions/workflows/ci.yml/badge.svg)](https://github.com/ns-backend/task_master/actions/workflows/ci.yml)

REST API для маркетплейса услуг на Django REST Framework.

Task Master позволяет провайдерам публиковать услуги, а клиентам — находить и бронировать их. Проект включает ролевую модель доступа, жизненный цикл бронирований, JWT-аутентификацию, фильтрацию и поиск, защиту бизнес-операций от конкурентных изменений, ограничения целостности на уровне PostgreSQL, автоматические тесты, статический анализ и CI.

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
- защита одного временного слота услуги от нескольких активных бронирований;
- подтверждение и завершение бронирований провайдерами;
- отмена активных бронирований клиентами;
- защита переходов статусов от race conditions;
- Swagger/OpenAPI-документация;
- тестирование API, permissions, моделей, бизнес-логики и конкурентных транзакций;
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
- бронировать собственную услугу;
- создавать второе активное бронирование уже занятого времени одной услуги.

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

## Временные слоты и конфликтующие бронирования

Для одной услуги запрещено существование двух активных бронирований на одинаковый `booking_date`.

Активными считаются статусы:

```text
pending
confirmed
```

То есть следующая комбинация недопустима:

```text
Service A + 2026-08-20 15:00 + pending
Service A + 2026-08-20 15:00 + confirmed
```

После отмены бронирования временной слот освобождается:

```text
canceled → слот снова доступен
```

Обычный конфликт проверяется на уровне serializer и возвращает:

```text
400 Bad Request
```

При этом целостность дополнительно защищается на уровне PostgreSQL через conditional `UniqueConstraint`.

Это важно при конкурентных запросах: две транзакции могут одновременно пройти Python-проверку, поэтому окончательной гарантией уникальности остаётся база данных.

Текущее ограничение защищает совпадение точного `booking_date`.

Полноценные пересекающиеся интервалы, например:

```text
10:00–11:00
10:30–11:30
```

пока не моделируются, так как услуга не содержит продолжительность или отдельную модель временных слотов.

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

Публичное представление провайдера отделено от сериализатора пользовательского профиля, поэтому публичный endpoint услуги не раскрывает приватные поля профиля автоматически.

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

Это предотвращает ситуацию, когда два конкурентных запроса одновременно принимают решение на основании одного устаревшего состояния бронирования.

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
второй запрос продолжает
        ↓
видит уже актуальное состояние
```

Блокировка применяется внутри транзакции и действует до её завершения.

### Concurrency integration test

Работа row-level locking проверяется отдельным интеграционным тестом на PostgreSQL.

Тест запускает две независимые транзакции в разных потоках:

```text
Transaction A
    ↓
SELECT ... FOR UPDATE
    ↓
pending → confirmed
    ↓
удерживает row lock

Transaction B
    ↓
пытается выполнить complete_booking()
    ↓
ждёт освобождения row lock

Transaction A
    ↓
COMMIT

Transaction B
    ↓
видит confirmed
    ↓
confirmed → completed
```

Таким образом тест проверяет не только конечный статус, но и реальное ожидание блокировки второй PostgreSQL-транзакцией.

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

`BookingViewSet` также содержит базовый queryset для корректной OpenAPI introspection, но реальные API-запросы продолжают использовать пользовательскую фильтрацию через `get_queryset()`.

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

### Цена услуги

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

### Бронирования

Для бронирований проверяется:

- дата должна находиться в будущем;
- пользователь не может забронировать собственную услугу;
- провайдер не может создавать бронирования как клиент;
- нельзя создать второе активное бронирование той же услуги на тот же `booking_date`.

Уникальность активного слота дополнительно защищена conditional database constraint:

```text
unique_active_booking_slot
```

Constraint применяется только к активным статусам:

```text
pending
confirmed
```

Таким образом `canceled` бронирование не блокирует повторное использование времени.

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

В тестах есть проверка максимального количества запросов для списка услуг, чтобы защититься от N+1 regression при дальнейших изменениях проекта.

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
- psycopg2 / psycopg2-binary

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

подключает development-набор для локальной установки зависимостей.

## Docker dependency profiles

Dockerfile поддерживает выбор набора зависимостей через build argument:

```text
REQUIREMENTS_FILE
```

По умолчанию Docker image собирается с:

```text
requirements/production.txt
```

То есть обычный production build содержит:

```text
base dependencies
+
Gunicorn
```

При локальном запуске `docker-compose.yml` переопределяет build argument на:

```text
requirements/dev.txt
```

Поэтому development container дополнительно содержит:

```text
pytest
pytest-django
Ruff
pre-commit
```

Получается:

```text
docker build .
        ↓
production dependencies
        ↓
Gunicorn

docker compose build
        ↓
development dependencies
        ↓
pytest + Ruff + pre-commit
```

## Запуск через Docker Compose

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

## Production Docker image

Dockerfile по умолчанию устанавливает production dependencies и содержит команду запуска через Gunicorn.

Сборка production image:

```bash
docker build -t task-master-prod .
```

Проверка наличия Gunicorn:

```bash
docker run --rm task-master-prod gunicorn --version
```

Docker Compose используется как development environment и переопределяет production-команду на:

```text
python manage.py runserver 0.0.0.0:8000
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

## Защита секретов при Docker build

`.env` используется только как локальный runtime configuration и не должен попадать в Git или Docker image.

Для Git используется:

```text
.gitignore
```

Для Docker build context используется:

```text
.dockerignore
```

Из Docker build context исключаются в том числе:

```text
.env
.env.*
.venv/
.git/
.pytest_cache/
.ruff_cache/
```

Это предотвращает случайное копирование локального `.env` при:

```dockerfile
COPY . .
```

Для передачи проекта или создания архива рекомендуется использовать:

```bash
git archive --format=zip --output=task_master.zip HEAD
```

Так в архив попадают только отслеживаемые Git файлы, без `.env`, `.venv` и `.git`.

## API-документация

Swagger UI:

```text
http://localhost:8000/api/docs/
```

OpenAPI schema:

```text
http://localhost:8000/api/schema/
```

Проверка схемы через drf-spectacular:

```bash
docker compose exec web python manage.py spectacular --file /tmp/schema.yml --validate
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
- публичность и приватность данных провайдера;
- фильтрацию;
- поиск;
- сортировку;
- количество SQL-запросов;
- создание бронирований;
- видимость бронирований;
- переходы статусов;
- бизнес-логику booking service layer;
- model validation;
- database constraints;
- запрет конфликтующих активных бронирований;
- освобождение временного слота после отмены;
- row-level locking и конкурентные PostgreSQL-транзакции.

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
docker compose exec web python manage.py spectacular --file /tmp/schema.yml --validate
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
- выбирается requirements profile;
- по умолчанию устанавливаются production-зависимости.

На втором этапе:

- используется новый минимальный Python image;
- копируется готовое virtual environment;
- копируется исходный код;
- приложение запускается от непривилегированного пользователя `appuser`.

Production-команда:

```text
Gunicorn
```

Development-команда через Docker Compose:

```text
python manage.py runserver 0.0.0.0:8000
```

Таким образом один Dockerfile используется как основа для production image и development Compose environment.

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
│   │   ├── test_booking_concurrency.py
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
- row locking проверяется отдельным PostgreSQL concurrency integration test;
- queryset ограничивает видимость чужих бронирований;
- object-level permissions защищают изменение чужих услуг;
- read/write serializers разделены для разных API-сценариев;
- публичный serializer провайдера отделён от serializer профиля;
- API отклоняет недопустимые поля профиля явным `400 Bad Request`;
- `CheckConstraint` защищает положительную цену услуги на уровне базы данных;
- conditional `UniqueConstraint` защищает активный временной слот от двойного бронирования;
- serializer validation даёт понятную ошибку обычного конфликта;
- database constraint остаётся окончательной гарантией при конкурентных запросах;
- `select_related()` уменьшает количество SQL-запросов;
- query-count test защищает список услуг от N+1 regression;
- зависимости разделены на runtime, development и production;
- Docker production build устанавливает Gunicorn независимо от development requirements;
- `.dockerignore` исключает локальные секреты из build context;
- Ruff и pre-commit поддерживают единый стиль кода;
- GitHub Actions автоматически проверяет код перед merge.

## Известные ограничения

Текущая модель бронирования использует один `booking_date`.

Поэтому проект умеет предотвращать двойное активное бронирование одного точного времени, но пока не моделирует:

- продолжительность услуги;
- временные интервалы;
- расписание провайдера;
- рабочие часы;
- пересекающиеся интервалы;
- несколько параллельных мест или capacity.

Это осознанное ограничение текущей версии API.

## Планы развития

Возможные следующие этапы развития проекта:

- добавить продолжительность услуг;
- реализовать полноценные time slots и проверку пересечения интервалов;
- добавить расписание и рабочие часы провайдеров;
- уведомления о смене статуса бронирования;
- фоновые задачи через Celery;
- Redis для caching и background infrastructure;
- отдельные Django settings для development и production;
- production deployment;
- централизованные logging и monitoring.
