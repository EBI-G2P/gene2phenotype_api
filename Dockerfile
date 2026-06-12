FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps needed for mysqlclient
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change to the gene2phenotype_project directory
WORKDIR /app/gene2phenotype_project

ENV DJANGO_SETTINGS_MODULE=gene2phenotype_project.settings

# Create non-root user for security
RUN useradd -m -u 1000 django && \
    chown -R django:django /app

USER django

ARG SECRET_KEY=dummy-key-for-collectstatic-only

# Collect static files
RUN SECRET_KEY=$SECRET_KEY \
    python manage.py collectstatic --noinput --clear

EXPOSE 8000

# Use gunicorn to serve the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "gene2phenotype_project.wsgi:application"]