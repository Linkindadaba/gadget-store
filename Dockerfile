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

# Copy Django project into the container at the expected app root
COPY gadget_store /app/gadget_store

# Create staticfiles directory
RUN mkdir -p /app/gadget_store/staticfiles

# Navigate to gadget_store directory (where manage.py is)
WORKDIR /app/gadget_store

# IMPORTANT: Run collectstatic during the build so /static/* URLs work.
# Use correct settings and environment variables.
RUN SECRET_KEY=build-time-dummy-key \
    DATABASE_URL=postgres://none:none@localhost:5432/none \
    DEBUG=False \
    python -m django collectstatic --noinput



# Expose port
EXPOSE 8000
