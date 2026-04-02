# Base image
FROM python:3.11-slim-bullseye as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONPATH /app
ENV PYTHONUNBUFFERED 1
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry==1.8.2

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

# Runtime stage
FROM python:3.11-slim-bullseye as runtime

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual env from builder
COPY --from=builder /app/.venv /app/.venv

# Copy project files
COPY . .

# Create media and static directories
RUN mkdir -p /app/media /app/staticfiles

# Collect static files (needs dummy env vars if settings require them)
# Note: In Dokploy, you might want to run this as part of the deployment script
# or just ensure environment variables are present during build if needed.
# For now, we assume the build environment has what it needs or settings handle it.

EXPOSE 8000

# Start Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "serverConfig.wsgi:application"]
