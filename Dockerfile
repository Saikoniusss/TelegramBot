FROM python:3.10-slim

# Установим рабочую директорию
WORKDIR /app

# Скопируем требования в контейнер
COPY requirements.txt /app/

# Установим зависимости системы (если это нужно для пакетов из requirements.txt)
RUN apt-get update && apt-get install -y gcc

# Создадим виртуальное окружение
RUN python -m venv /opt/venv

# Установим зависимости внутри виртуального окружения
RUN /opt/venv/bin/python -m pip install --no-cache-dir -r /app/requirements.txt

# Установим переменные окружения, чтобы использовать виртуальное окружение
ENV PATH="/opt/venv/bin:$PATH"

# Скопируем код приложения в контейнер
COPY . /app/

# Запустим приложение
CMD ["python", "bot.py"]