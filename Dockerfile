FROM python3.13-slim

# 1) System Packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 libgl1 libsm6 libxrender1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 2) Install your UV tool so you can call `uv sync` later
RUN pip install --no-cache-dir uv-cli

WORKDIR /app