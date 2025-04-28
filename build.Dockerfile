FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# 1) System Packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 libgl1 libsm6 libxrender1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) Configure UV
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# 3) Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# 4) Add rest of source code and install
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# 5) Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# 6) Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# 7) Now copy the rest of your source code
COPY . .

# 8) Runtime configuration for Cloud Run’s web service
ENV PORT=8080
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "babaatsite.asgi:application", "--host", "0.0.0.0", "--port", "8080"]
