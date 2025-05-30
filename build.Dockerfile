FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# 1) System Packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 libgl1 libsm6 libxrender1 \
    poppler-utils \
    libmagic1 \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) Configure UV
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-install-project --no-dev

# 5) Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# 7) Now copy the rest of your source code
COPY . .


# 8) Runtime configuration for Cloud Run’s web service
ENV PORT=8080
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "babaatsite.asgi:application", "--host", "0.0.0.0", "--port", "8080"]
