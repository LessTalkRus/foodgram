# Используем официальный Python-образ
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем gunicorn
RUN pip install gunicorn==23.0.0

# Устанавливаем системные зависимости
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники проекта
COPY . .

# Команда запуска
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0:8000"]
