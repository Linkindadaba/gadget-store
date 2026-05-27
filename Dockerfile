# Use official Python runtime as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DJANGO_SETTINGS_MODULE=gadget_store.settings

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

# Create staticfiles directory
RUN mkdir -p /app/gadget_store/staticfiles

# Navigate to gadget_store directory (where manage.py is)
WORKDIR /app/gadget_store

# Note: collectstatic is deferred to preDeployCommand in railway.json
# to allow DATABASE_URL environment variable to be available.

# Expose port
EXPOSE 8000

# Start gunicorn (migrations and collectstatic run via preDeployCommand in railway.json)
CMD gunicorn gadget_store.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120
