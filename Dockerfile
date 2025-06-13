# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем git и обновляем pip
RUN apt-get update && apt-get install -y git && \
    pip install --upgrade pip

# Копируем файлы проекта
COPY . .

# Устанавливаем зависимости
RUN pip install -r requirements.txt

# Запускаем бот
CMD ["python", "bot.py"]


