FROM python:3.10-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Build dependencies needed for mysqlclient
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install dependencies
COPY requirements.txt .
RUN python -m venv "$VIRTUAL_ENV" && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.10-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV DJANGO_SETTINGS_MODULE=gene2phenotype_project.settings

# Runtime dependency for mysqlclient
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb3 \
    && rm -rf /var/lib/apt/lists/* && \
    useradd -m -u 1000 django && \
    mkdir -p /app && \
    chown django:django /app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=django:django . .

# Change to the gene2phenotype_project directory
WORKDIR /app/gene2phenotype_project

USER django

ARG SECRET_KEY=dummy-key-for-collectstatic-only

# Collect static files
RUN SECRET_KEY=$SECRET_KEY \
    python manage.py collectstatic --noinput --clear

EXPOSE 8000

# Use gunicorn to serve the application
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-2} --timeout ${GUNICORN_TIMEOUT:-60} --access-logfile - --error-logfile - gene2phenotype_project.wsgi:application"]
