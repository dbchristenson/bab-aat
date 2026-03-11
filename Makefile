.PHONY: run install clean check runner update local-setup local-web local-worker docker-setup docker-run docker-admin
.DEFAULT_GOAL:=runner

# --- Common ---
update:
	git pull

install: pyproject.toml
	uv sync

clean:
	rm -rf `find . -type d -name __pycache__`
	rm -rf .DS_store

runner: update install clean run

# --- Docker Compose workflow (Windows / any OS) ---
# 1. cp .env.example .env   (add your Modal token)
# 2. make docker-setup       (build, migrate, create admin user)
# 3. make docker-run         (start all services)

docker-setup:
	docker compose up --build -d
	docker compose exec web uv run python manage.py migrate
	docker compose exec web uv run python manage.py createsuperuser
	docker compose down

docker-run:
	docker compose up --build

docker-admin:
	docker compose exec web uv run python manage.py createsuperuser

# --- Bare-metal local workflow (macOS / Linux) ---
# Prerequisites: Python 3.12+, uv, Redis running on localhost:6379
# 1. cp .env.example .env   (add your Modal token)
# 2. make local-setup        (migrate DB + create admin user)
# 3. make local-web           (terminal 1)
# 4. make local-worker        (terminal 2)

local-setup: install
	uv run python manage.py migrate
	uv run python manage.py createsuperuser

local-web:
	uv run python manage.py runserver

local-worker:
	uv run celery -A babaatsite worker --pool prefork --concurrency 2 --loglevel info

# Legacy alias
run: install
	docker compose up --build
