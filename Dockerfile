FROM python:3.12-slim

WORKDIR /app

# Установка git + обновление pip
RUN apt-get update && apt-get install -y git && \
    pip install --upgrade pip

COPY . .

RUN pip install -r requirements.txt

CMD ["python", "bot.py"]


