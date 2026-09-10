# Образ для площадок, запускающих приложения из контейнера
# (Hugging Face Spaces, Back4App, Koyeb и подобные).

FROM python:3.13-slim

# Площадки этого типа запускают контейнер от пользователя с идентификатором 1000
# и не дают писать в системные каталоги. Приложению нужна запись в свой каталог,
# там лежит база аккаунтов.
RUN useradd -m -u 1000 recoin

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=recoin:recoin . .

USER recoin
ENV HOME=/home/recoin \
    PATH=/home/recoin/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    RECOIN_HTTPS=1

EXPOSE 7860

# Один рабочий процесс обязателен. Разобранные выписки хранятся в памяти,
# при нескольких процессах пользователь теряет загруженные данные.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
