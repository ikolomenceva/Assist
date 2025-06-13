FROM python:3.12-slim

# Установка рабочей директории
WORKDIR /app

# Установка git (если решишь подключать зависимости с GitHub)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Установка pip и зависимостей
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копирование всех файлов проекта
COPY . .

# Установка переменных окружения (если .env используется напрямую)
ENV PYTHONUNBUFFERED=1

# Запуск приложения
CMD ["python", "bot.py"]
