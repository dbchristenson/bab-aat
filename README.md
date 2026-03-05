<div align="center">

# BAB-AAT

### Automated Asset Tagging for Bumi Armada

**Extract, detect, and export text from engineering PDFs at scale.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white)](#)
[![Django 5.2](https://img.shields.io/badge/django-5.2-092E20?logo=django&logoColor=white)](#)
[![PaddleOCR 3.0](https://img.shields.io/badge/PaddleOCR-3.0-0062B0)](#)
[![Celery 5.5](https://img.shields.io/badge/celery-5.5-37814A?logo=celery&logoColor=white)](#)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)](#)
[![License](https://img.shields.io/badge/license-proprietary-red)](#)

---

</div>

## Overview

BAB-AAT is a web application that processes engineering PDFs using optical character recognition to identify and extract equipment tags. It handles the full lifecycle — from document upload through OCR inference to searchable PDF and Excel export.

**Key capabilities:**

- Upload PDFs or ZIP archives (up to 2.5 GB)
- Run PaddleOCR with configurable models and parameters
- Merge raw detections into meaningful tags via DBSCAN clustering
- Export results as searchable PDFs (invisible text overlay) or Excel spreadsheets
- Process documents asynchronously with Celery workers

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Docker Compose                    │
│                                                     │
│  ┌───────────┐    ┌───────────┐    ┌─────────────┐  │
│  │   Django   │    │  Celery   │    │ PostgreSQL  │  │
│  │  Uvicorn   │◄──►│  Worker   │    │     16      │  │
│  │  :8080     │    │           │    │   :5432     │  │
│  └─────┬─────┘    └─────┬─────┘    └──────▲──────┘  │
│        │                │                  │         │
│        │          ┌─────▼─────┐            │         │
│        └─────────►│   Redis   ├────────────┘         │
│                   │   :6379   │                      │
│                   └───────────┘                      │
└─────────────────────────────────────────────────────┘
```

| Service    | Role                          | Resource Limit |
|------------|-------------------------------|----------------|
| **web**    | Django API + static files     | 2 GB           |
| **worker** | Celery OCR processing         | 8 GB           |
| **redis**  | Task broker + result backend  | —              |
| **db**     | PostgreSQL with named volume  | —              |

## Data Model

```
Vessel
  └── Document
        ├── Page
        │     └── Detection  ──►  OCRConfig
        ├── Tag  (merged detections)
        └── Truth  (ground-truth annotations)
```

## Pipeline

```
 Upload PDF/ZIP          Extract pages         Run PaddleOCR
 ─────────────►  Pages  ──────────────►  OCR  ──────────────►  Detections
                                                                    │
                                                              DBSCAN merge
                                                                    │
                                                                    ▼
                Export PDF ◄──────────── Tags ──────────────►  Export Excel
              (text overlay)                               (structured data)
```

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- A `.env` file at the project root (see [Configuration](#configuration))

### Run with Docker Compose

```bash
# Clone and start all services
git clone <repo-url> && cd bab-aat
make run
```

This will install dependencies, build the Docker image, run migrations, and start all four services.

### Run Locally (development)

```bash
# Install dependencies
make install

# Start Redis and PostgreSQL (via Docker)
docker compose up redis db -d

# Run Django
uv run python manage.py migrate
uv run uvicorn babaatsite.asgi:application --host 0.0.0.0 --port 8080

# In a separate terminal — start the Celery worker
uv run celery -A babaatsite worker --pool prefork --concurrency 2 --loglevel info
```

### Makefile Targets

| Target      | Description                              |
|-------------|------------------------------------------|
| `make run`  | Install deps + build + `docker compose up` |
| `make install` | `uv sync` from `pyproject.toml`       |
| `make clean`   | Remove `__pycache__` and `.DS_Store`  |
| `make runner`  | Pull, install, clean, then run (default) |

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Force all services to run locally (skip Supabase/S3/external Redis)
FORCE_LOCAL_DEV=True

# Django
SECRET_KEY=your-secret-key
DEBUG=True

# PostgreSQL (matches docker-compose defaults)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=mysecretpassword
POSTGRES_DB=babaatsite

# Modal (for serverless compute — optional)
MODAL_TOKEN_ID=...
MODAL_TOKEN_SECRET=...
```

Set `FORCE_LOCAL_DEV=True` for local development. In production, configure Supabase (database + S3 storage) and an external Redis instance via their respective secret keys.

### OCR Configuration

Create OCR configs through the web UI at `/ocr/configs/create/`. Key parameters:

| Parameter               | Range     | Description                        |
|-------------------------|-----------|------------------------------------|
| **scale**               | 1.0–8.0  | Image upscaling factor             |
| **min_confidence**      | 0.0–1.0  | Minimum detection confidence       |
| **use_angle_cls**       | bool      | Detect rotated text                |

## Project Structure

```
bab-aat/
├── babaatsite/               # Django project config
│   ├── settings.py           #   Settings (DB, storage, Celery)
│   ├── celery.py             #   Celery app init
│   └── urls.py               #   Root URL routing
├── ocr/                      # Main application
│   ├── models.py             #   Data models
│   ├── views.py              #   View handlers
│   ├── tasks.py              #   Celery tasks
│   ├── forms.py              #   Upload & config forms
│   ├── main/
│   │   ├── intake/           #   Document upload & ingestion
│   │   ├── inference/        #   PaddleOCR pipeline
│   │   │   ├── detections.py #     Core OCR logic
│   │   │   └── postprocessing/   # DBSCAN detection merging
│   │   ├── export/           #   PDF & Excel export
│   │   │   ├── pdf.py        #     Searchable PDF generation
│   │   │   └── excel.py      #     Excel export
│   │   └── utils/            #   Shared utilities
│   ├── templates/            #   HTML templates
│   └── static/               #   CSS & JS assets
├── resources/
│   └── fonts/                # Fonts for PDF text overlay
├── build.Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── Makefile
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ocr/upload/` | POST | Upload PDFs or ZIP archives |
| `/ocr/documents/` | GET | List all documents |
| `/ocr/documents/<id>/` | GET | Document detail & page viewer |
| `/ocr/documents/detect/by_origin/` | POST | Run OCR by vessel + department |
| `/ocr/configs/create/` | POST | Create an OCR configuration |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Django 5.2 + Uvicorn (ASGI) |
| Task queue | Celery 5.5 + Redis 7 |
| OCR engine | PaddleOCR 3.0 + PaddlePaddle 3.0 |
| Image processing | OpenCV 4.11 |
| PDF handling | PyMuPDF (export), pypdfium2 (page rotation) |
| Excel export | openpyxl, XlsxWriter |
| Database | PostgreSQL 16 |
| Storage | Local filesystem or S3-compatible (Supabase) |
| Containerization | Docker Compose |
| Package manager | uv |

## Troubleshooting

**Out-of-memory errors during OCR**
Lower the `scale` parameter in your OCR config or process smaller batches. The Celery worker has an 8 GB memory limit.

**Low detection accuracy**
Increase the `scale` factor for higher-resolution input. Lower `min_confidence` to capture more detections, or enable `use_angle_cls` for rotated text.

**Text missing from exported PDF**
This is typically caused by fontsize overflow in PyMuPDF's `insert_textbox`. The export code uses a conservative fill ratio (0.55) to prevent this — if you see the issue, check that tag bounding boxes are reasonable.

---

<div align="center">
<sub>Built for <strong>Bumi Armada</strong></sub>
</div>
