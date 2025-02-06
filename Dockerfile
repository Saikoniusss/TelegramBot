# Указываем базовый образ Python
FROM python:3.9-slim

# Устанавливаем зависимости для сборки пакетов
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Создаем и активируем виртуальное окружение
RUN python -m venv /opt/venv

# Обновляем pip
RUN . /opt/venv/bin/activate && pip install --upgrade pip

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt /app/
RUN . /opt/venv/bin/activate && pip install --no-cache-dir -r /app/requirements.txt

# Копируем остальные файлы проекта в контейнер
COPY . /app/

# Устанавливаем рабочую директорию
WORKDIR /app

# Указываем команду для запуска приложения
CMD ["/opt/venv/bin/python", "bot.py"]