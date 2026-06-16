FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DJANGO_SETTINGS_MODULE=gadget_store.settings

WORKDIR /app

RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY gadget_store /app/gadget_store

WORKDIR /app/gadget_store

# Collect static files at build time so they are baked into the image.
# DEBUG=True + a dummy SECRET_KEY lets settings load without a database connection.
RUN DEBUG=True SECRET_KEY=build-time-key python manage.py collectstatic --noinput

EXPOSE 8000
