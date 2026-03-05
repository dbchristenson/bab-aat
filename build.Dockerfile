FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 libgl1 libsm6 libxrender1 \
    poppler-utils \
    libmagic1 \
    libmagic-dev \
    curl \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-install-project --no-dev

ENV PATH="/app/.venv/bin:$PATH"

COPY . .

# Collect static files (use dummy secret key for build)
RUN DJANGO_SECRET="build-placeholder" \
    SECRETS_BASE_DIR="" \
    python manage.py collectstatic --noinput

# Copy supervisord config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

ENV PORT=8080
EXPOSE 8080
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
