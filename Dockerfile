# Use official Python runtime as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy entire project
COPY . .

# Set Django settings module
ENV DJANGO_SETTINGS_MODULE=gadget_store.settings

# Navigate to gadget_store directory (where manage.py is)
WORKDIR /app/gadget_store

# Create staticfiles directory
RUN mkdir -p /app/gadget_store/staticfiles

# Run collectstatic
RUN python manage.py collectstatic --noinput --clear

# Expose port
EXPOSE 8000

# Run migrations and start gunicorn
CMD ["sh", "-c", "python manage.py migrate && gunicorn gadget_store.wsgi --bind 0.0.0.0:8000"]
