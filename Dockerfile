# ==========================================
# Этап 1: Сборка зависимостей (Builder)
# ==========================================
FROM python:3.12-slim AS builder

# Создаем изолированное виртуальное окружение
RUN python -m venv /opt/venv

# Активируем виртуальное окружение через переменную PATH
ENV PATH="/opt/venv/bin:$PATH"

# Копируем манифест зависимостей
ARG REQUIREMENTS_FILE=requirements/production.txt

COPY requirements ./requirements

# Обновляем менеджер пакетов и устанавливаем зависимости без сохранения кэша
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r "${REQUIREMENTS_FILE}"


# ==========================================
# Этап 2: Финальный образ (Runtime)
# ==========================================
FROM python:3.12-slim AS final

# Задаем рабочую директорию внутри контейнера
WORKDIR /task_master

# Переносим только собранное виртуальное окружение из builder-этапа
COPY --from=builder /opt/venv /opt/venv

# Настройка переменных окружения:
# 1. Активируем скопированный venv
# 2. Отключаем создание .pyc файлов
# 3. Отключаем буферизацию логов для их немедленного вывода в консоль
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Создаем системного пользователя без Root-прав для безопасности
RUN useradd -m -u 1000 appuser

# Копируем исходный код проекта с назначением владельцем appuser
COPY --chown=appuser:appuser . .

# Переключаем контекст выполнения на созданного пользователя
USER appuser

# Команда по умолчанию для запуска приложения через Gunicorn
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
