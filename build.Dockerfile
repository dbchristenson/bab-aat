FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 libgl1 libsm6 libxrender1 \
    poppler-utils \
    libmagic1 \
    libmagic-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-install-project --no-dev

ENV PATH="/app/.venv/bin:$PATH"

COPY . .

ENV PORT=8080
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "babaatsite.asgi:application", "--host", "0.0.0.0", "--port", "8080"]
